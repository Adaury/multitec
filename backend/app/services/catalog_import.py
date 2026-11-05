"""Importación masiva de productos del catálogo desde uno o varios archivos CSV o Excel (.xlsx).
Pensado para cargar de golpe una lista de precios en vez de crear producto por producto.

Reglas, a propósito conservadoras:
  * Una celda vacía NUNCA borra un dato que el producto ya tiene: solo se actualiza lo que viene lleno.
  * Se reconoce un producto existente por su `codigo` o, si no viene, por su nombre (sin importar
    mayúsculas ni tildes); si existe se actualiza, si no se crea.
  * Un producto nuevo necesita categoría. La categoría se busca por nombre ("Cámaras IP") o por
    ruta ("CCTV > Cámaras IP"); si el nombre existe en varias ramas se pide la ruta.
  * Las filas con error no frenan al resto: se informan una por una.
  * `dry_run=True` calcula y devuelve el mismo resumen sin tocar la base de datos.
  * Con `create_categories=True`, una categoría que no existe se crea (con su ruta, «Alarmas > Sirenas»).
  * Varios archivos se procesan como uno solo: un producto del primero ya «existe» para el segundo.
"""

import csv
import io
import re
import unicodedata
from typing import Any

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.product import Product, resolve_code_prefix
from app.schemas.product import ProductCreate, ProductUpdate
from app.services.code_generator import next_code
from app.services.spreadsheets import build_csv_semicolon, build_xlsx, read_rows

MAX_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000
EXAMPLE_PREFIX = "ejemplo"

TEMPLATE_HEADERS = [
    "Nombre",
    "Categoria",
    "Unidad",
    "Precio",
    "Costo",
    "Marca",
    "Modelo",
    "Descripcion",
    "Etiquetas",
    "Sinonimos",
    "Codigo",
]
# Plantillas listas para llenar: nombres reales y la categoría ya puesta; el precio y el costo se dejan vacíos
# para que cada empresa ponga los suyos (un producto sin precio entra con precio 0 marcado «estimado»).
TEMPLATE_KITS: dict[str, tuple[str, list[list[str]]]] = {
    "alarma": (
        "plantilla_materiales_alarma",
        [
            ["Panel de alarma 8 zonas", "Alarmas > Paneles", "unidad", "", "", "", "", "Panel de alarma cableado 8 zonas expandible", "alarma;panel", "central de alarma"],
            ["Teclado LCD para panel de alarma", "Alarmas > Teclados", "unidad", "", "", "", "", "", "alarma;teclado", ""],
            ["Sensor de movimiento PIR", "Alarmas > Sensores", "unidad", "", "", "", "", "Detector infrarrojo de movimiento para interior", "alarma;sensor;pir", "detector de movimiento"],
            ["Sensor de movimiento PIR inmune a mascotas", "Alarmas > Sensores", "unidad", "", "", "", "", "", "alarma;sensor;pir;mascotas", ""],
            ["Contacto magnético para puerta", "Alarmas > Sensores", "unidad", "", "", "", "", "", "alarma;contacto magnetico", "magnetico de puerta"],
            ["Contacto magnético de alto tráfico (portón)", "Alarmas > Sensores", "unidad", "", "", "", "", "", "alarma;contacto magnetico;porton", ""],
            ["Detector de humo", "Alarmas > Sensores", "unidad", "", "", "", "", "", "alarma;humo;incendio", ""],
            ["Detector de rotura de vidrio", "Alarmas > Sensores", "unidad", "", "", "", "", "", "alarma;vidrio", ""],
            ["Sirena exterior con estrobo", "Alarmas > Sirenas", "unidad", "", "", "", "", "", "alarma;sirena;exterior", ""],
            ["Sirena interior 30 W", "Alarmas > Sirenas", "unidad", "", "", "", "", "", "alarma;sirena;interior", ""],
            ["Botón de pánico", "Alarmas > Accesorios", "unidad", "", "", "", "", "", "alarma;panico", ""],
            ["Control remoto (llavero) para alarma", "Alarmas > Accesorios", "unidad", "", "", "", "", "", "alarma;control remoto", ""],
            ["Comunicador GSM / 4G para alarma", "Alarmas > Comunicadores", "unidad", "", "", "", "", "", "alarma;comunicador;gsm", ""],
            ["Módulo de comunicación IP para alarma", "Alarmas > Comunicadores", "unidad", "", "", "", "", "", "alarma;comunicador;ip", ""],
            ["Batería 12 V 7 Ah", "Alarmas > Baterías", "unidad", "", "", "", "", "", "alarma;bateria;12v", "bateria de respaldo"],
            ["Transformador 16.5 V para panel", "Alarmas > Accesorios", "unidad", "", "", "", "", "", "alarma;transformador", ""],
            ["Cable de alarma 4 hilos 22 AWG (rollo 305 m)", "Alarmas > Cableado", "rollo", "", "", "", "", "", "alarma;cable;4 hilos", "cable de alarma"],
            ["Gabinete metálico para panel", "Alarmas > Accesorios", "unidad", "", "", "", "", "", "alarma;gabinete", ""],
        ],
    ),
    "ferreteria": (
        "plantilla_materiales_ferreteria",
        [
            ["Tornillo autorroscante 8 x 1\" (caja 100)", "Ferretería > Tornillería", "caja", "", "", "", "", "", "tornillo;ferreteria", ""],
            ["Tornillo para concreto 1/4 x 1-1/4\"", "Ferretería > Tornillería", "unidad", "", "", "", "", "", "tornillo;concreto;ferreteria", "tapcon"],
            ["Taco plástico (fisher) 1/4\" (bolsa 100)", "Ferretería > Anclajes", "bolsa", "", "", "", "", "", "taco;anclaje;ferreteria", "tarugo;fisher"],
            ["Ancla de expansión 3/8\"", "Ferretería > Anclajes", "unidad", "", "", "", "", "", "ancla;anclaje;ferreteria", ""],
            ["Abrazadera EMT 3/4\"", "Ferretería > Abrazaderas y grapas", "unidad", "", "", "", "", "", "abrazadera;emt;ferreteria", "grapa"],
            ["Grapa para cable con clavo (bolsa 100)", "Ferretería > Abrazaderas y grapas", "bolsa", "", "", "", "", "", "grapa;cable;ferreteria", ""],
            ["Amarre plástico 8\" (bolsa 100)", "Ferretería > Amarres y cintas", "bolsa", "", "", "", "", "", "amarre;tie wrap;ferreteria", "tie wrap;cincho"],
            ["Cinta aislante negra", "Ferretería > Amarres y cintas", "unidad", "", "", "", "", "", "cinta;aislante;ferreteria", "tape"],
            ["Cinta doble cara", "Ferretería > Amarres y cintas", "unidad", "", "", "", "", "", "cinta;doble cara;ferreteria", ""],
            ["Silicón transparente (tubo)", "Ferretería > Selladores", "unidad", "", "", "", "", "", "silicon;sellador;ferreteria", "silicona"],
            ["Broca para concreto 1/4\"", "Ferretería > Brocas", "unidad", "", "", "", "", "", "broca;concreto;ferreteria", "mecha"],
            ["Broca para metal 1/8\"", "Ferretería > Brocas", "unidad", "", "", "", "", "", "broca;metal;ferreteria", "mecha"],
            ["Caja eléctrica rectangular 2 x 4", "Ferretería > Cajas y tapas", "unidad", "", "", "", "", "", "caja;electrica;ferreteria", "caja 2x4"],
            ["Caja de registro exterior IP65", "Ferretería > Cajas y tapas", "unidad", "", "", "", "", "", "caja;registro;exterior;ferreteria", ""],
            ["Tapa ciega 2 x 4", "Ferretería > Cajas y tapas", "unidad", "", "", "", "", "", "tapa;ferreteria", ""],
            ["Conector EMT 3/4\"", "Ferretería > Conectores y uniones", "unidad", "", "", "", "", "", "conector;emt;ferreteria", ""],
            ["Unión EMT 3/4\"", "Ferretería > Conectores y uniones", "unidad", "", "", "", "", "", "union;emt;ferreteria", ""],
            ["Disco de corte para metal 4-1/2\"", "Ferretería > Herramientas y consumibles", "unidad", "", "", "", "", "", "disco;corte;ferreteria", ""],
        ],
    ),
}

TEMPLATE_EXAMPLES = [
    ["EJEMPLO Camara IP 4MP bala", "Camaras Bullet", "unidad", "3500", "2400", "Hikvision", "DS-2CD1043", "Camara IP 4MP exterior", "camara;ip;4mp", "camara bala;camara exterior", ""],
    ["EJEMPLO Caja de cable UTP Cat6 305m", "UTP Categoria 6", "caja", "6800", "5200", "", "", "", "cable;utp;caja de cable", "caja de utp", ""],
]

# Encabezado normalizado -> campo interno.
_ALIASES: dict[str, str] = {}
for _field, _names in {
    "name": ["nombre", "producto", "articulo", "item", "name"],
    "category": ["categoria", "category", "grupo", "linea"],
    "unit": ["unidad", "unit", "und", "unidad_de_venta"],
    "price": ["precio", "precio_venta", "precio_de_venta", "price", "pvp"],
    "cost": ["costo", "cost", "costo_unitario", "precio_costo"],
    "brand": ["marca", "brand"],
    "model": ["modelo", "model"],
    "commercial_description": ["descripcion", "descripcion_comercial", "description"],
    "technical_description": ["descripcion_tecnica", "ficha_tecnica", "especificaciones"],
    "notes": ["notas", "nota", "observaciones"],
    "tags": ["etiquetas", "tags", "palabras_clave"],
    "synonyms": ["sinonimos", "synonyms", "tambien_conocido_como"],
    "install_minutes": ["minutos_instalacion", "minutos_de_instalacion", "install_minutes", "minutos"],
    "labor_role": ["rol_mano_obra", "rol", "labor_role", "rol_de_mano_de_obra"],
    "resolution_mp": ["resolucion_mp", "megapixeles", "mp", "resolucion"],
    "storage_capacity_gb": ["almacenamiento_gb", "capacidad_gb", "storage_capacity_gb"],
    "channel_capacity": ["canales", "puertos", "capacidad_canales", "channel_capacity"],
    "pack_size": ["unidades_por_paquete", "unidades_por_bolsa", "unidades_por_caja", "pack_size", "paquete_de"],
    "priority": ["prioridad", "priority"],
    "code": ["codigo", "code", "sku"],
}.items():
    for _n in _names:
        _ALIASES[_n] = _field

_NUMERIC = {"price", "cost", "install_minutes", "resolution_mp", "storage_capacity_gb"}
_INTEGER = {"channel_capacity", "priority", "pack_size"}
_LISTS = {"tags", "synonyms"}


def _fold(text: str) -> str:
    """Minúsculas, sin tildes y con espacios simples, para comparar nombres sin sorpresas."""
    stripped = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _header_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _fold(text)).strip("_")


def parse_number(raw: str) -> float:
    """Acepta "1250", "1,250.50", "1.250,50", "RD$ 3,500" y "3500,5"."""
    text = re.sub(r"[^\d,.\-]", "", raw.strip())
    if not text or text in "-.,":
        raise ValueError(f"'{raw}' no es un número")
    if "," in text and "." in text:
        # El último separador es el decimal; el otro es de miles.
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        # "3500,5" -> decimal; "3,500" -> miles.
        text = text.replace(",", ".") if re.search(r",\d{1,2}$", text) else text.replace(",", "")
    try:
        return float(text)
    except ValueError:
        raise ValueError(f"'{raw}' no es un número") from None


def _split_list(raw: str) -> list[str]:
    parts = re.split(r"[;|,]", raw)
    seen: list[str] = []
    for part in parts:
        value = part.strip()
        if value and value.lower() not in [s.lower() for s in seen]:
            seen.append(value)
    return seen


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("latin-1")


def template_csv() -> bytes:
    """Plantilla para descargar. La línea `sep=;` hace que Excel separe en columnas sin importar la
    configuración regional; las filas EJEMPLO se ignoran al importar."""
    out = io.StringIO()
    out.write("sep=;\r\n")
    writer = csv.writer(out, delimiter=";", lineterminator="\r\n")
    writer.writerow(TEMPLATE_HEADERS)
    for row in TEMPLATE_EXAMPLES:
        writer.writerow(row)
    return ("﻿" + out.getvalue()).encode("utf-8")


TEMPLATE_WIDTHS = [42, 34, 10, 12, 12, 14, 14, 40, 30, 26, 14]


def template_file(kind: str, fmt: str) -> tuple[bytes, str]:
    """Plantilla por tipo («general», «alarma», «ferreteria») en CSV o Excel. Devuelve (contenido, nombre)."""
    if kind == "general":
        name, rows = "plantilla_catalogo", TEMPLATE_EXAMPLES
        if fmt == "csv":
            return template_csv(), f"{name}.csv"
    elif kind in TEMPLATE_KITS:
        name, rows = TEMPLATE_KITS[kind]
        rows = [r + [""] * (len(TEMPLATE_HEADERS) - len(r)) for r in rows]
    else:
        raise ValueError("Tipo de plantilla desconocido")
    if fmt == "xlsx":
        return build_xlsx(TEMPLATE_HEADERS, rows, "Productos", TEMPLATE_WIDTHS), f"{name}.xlsx"
    return build_csv_semicolon(TEMPLATE_HEADERS, rows), f"{name}.csv"


def export_catalog(db: Session, fmt: str) -> tuple[bytes, str]:
    """Todo el catálogo con las mismas columnas de la plantilla: se edita en Excel y se vuelve a subir
    (el código hace que cada fila actualice su producto en vez de crear otro)."""
    categories = {c.id: c for c in db.query(Category).all()}

    def path(category_id: int | None) -> str:
        parts, node = [], categories.get(category_id) if category_id else None
        while node is not None:
            parts.append(node.name)
            node = categories.get(node.parent_id) if node.parent_id else None
        return " > ".join(reversed(parts))

    rows = []
    for p in db.query(Product).order_by(Product.code).all():
        rows.append([
            p.name, path(p.category_id), p.unit, float(p.price or 0), float(p.cost) if p.cost is not None else "",
            p.brand or "", p.model or "", p.commercial_description or "", ";".join(p.tags or []),
            ";".join(p.synonyms or []), p.code,
        ])
    if fmt == "xlsx":
        return build_xlsx(TEMPLATE_HEADERS, rows, "Catálogo", TEMPLATE_WIDTHS), "catalogo.xlsx"
    return build_csv_semicolon(TEMPLATE_HEADERS, rows), "catalogo.csv"


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _fold(name)).strip("-") or "categoria"


class CategoryIndex:
    def __init__(self, db: Session):
        self.new_slugs: set[str] = set()
        categories = db.query(Category).all()
        by_id = {c.id: c for c in categories}
        self.by_name: dict[str, list[Category]] = {}
        self.by_path: dict[str, Category] = {}
        for c in categories:
            parts, node = [], c
            while node is not None:
                parts.append(node.name)
                node = by_id.get(node.parent_id)
            self.by_path[_fold(" > ".join(reversed(parts)))] = c
            self.by_name.setdefault(_fold(c.name), []).append(c)

    def find(self, raw: str) -> tuple[Category | None, str | None]:
        key = _fold(re.sub(r"\s*[>/]\s*", " > ", raw))
        if key in self.by_path:
            return self.by_path[key], None
        matches = self.by_name.get(key, [])
        if len(matches) == 1:
            return matches[0], None
        if len(matches) > 1:
            return None, f"La categoría '{raw}' existe en varias ramas; escribe la ruta completa (p. ej. 'Cableado > Otros')"
        return None, f"La categoría '{raw}' no existe"

    def find_or_create(self, db: Session, raw: str, dry_run: bool) -> tuple[Category | None, str | None, list[str]]:
        """Como `find`, pero crea la ruta que falte. Devuelve también los nombres de las categorías nuevas."""
        found, problem = self.find(raw)
        if found is not None or (problem and "varias ramas" in problem):
            return found, problem, []
        parts = [part.strip() for part in re.split(r"\s*[>/]\s*", raw) if part.strip()]
        if not parts:
            return None, "Falta la categoría", []
        created: list[str] = []
        parent: Category | None = None
        for depth in range(len(parts)):
            key = _fold(" > ".join(parts[: depth + 1]))
            node = self.by_path.get(key)
            if node is None and depth == 0:
                # Un primer nivel escrito solo ("Alarmas") puede ser una categoría que ya existe en otra rama.
                matches = [c for c in self.by_name.get(_fold(parts[0]), []) if c.parent_id is None]
                node = matches[0] if len(matches) == 1 else None
            if node is None:
                node = Category(name=parts[depth][:120], slug=self._unique_slug(db, parts[depth]), parent_id=parent.id if parent is not None else None)
                if not dry_run:
                    db.add(node)
                    db.flush()
                created.append(" > ".join(parts[: depth + 1]))
                self.by_path[key] = node
                self.by_name.setdefault(_fold(parts[depth]), []).append(node)
            parent = node
        return parent, None, created

    def _unique_slug(self, db: Session, name: str) -> str:
        base = _slug(name)
        taken = {s for (s,) in db.query(Category.slug).all()} | self.new_slugs
        slug, n = base, 2
        while slug in taken:
            slug, n = f"{base}-{n}", n + 1
        self.new_slugs.add(slug)
        return slug


def import_catalog(db: Session, data: bytes, user_id: int | None, dry_run: bool) -> dict[str, Any]:
    """Un solo archivo CSV o Excel (compatibilidad con la versión de un archivo)."""
    return import_catalog_files(db, [("archivo", data)], user_id, dry_run)


def import_catalog_files(
    db: Session,
    files: list[tuple[str, bytes]],
    user_id: int | None,
    dry_run: bool,
    create_categories: bool = False,
) -> dict[str, Any]:
    if not files:
        raise ValueError("No llegó ningún archivo")
    sheets: list[tuple[str, list[list[str]]]] = []
    for filename, data in files:
        try:
            rows = read_rows(data, filename)
        except ValueError as exc:
            raise ValueError(f"{filename}: {exc}") from None
        if not any(any(c.strip() for c in r) for r in rows):
            raise ValueError(f"{filename}: el archivo está vacío")
        sheets.append((filename, rows))

    ignored: list[str] = []
    parsed: list[tuple[str, dict[int, str], list[list[str]]]] = []
    for filename, rows in sheets:
        header_at = next(i for i, r in enumerate(rows) if any(c.strip() for c in r))
        header_row = rows[header_at]
        columns: dict[int, str] = {}
        for index, title in enumerate(header_row):
            field = _ALIASES.get(_header_key(title))
            if field and field not in columns.values():
                columns[index] = field
            elif title.strip() and title.strip() not in ignored:
                ignored.append(title.strip())
        if "name" not in columns.values():
            prefix = f"{filename}: " if len(files) > 1 else ""
            raise ValueError(f"{prefix}Falta la columna 'Nombre' (o 'Producto'). Usa la plantilla para empezar.")
        data_rows = rows[header_at + 1 :]
        if len(data_rows) > MAX_ROWS:
            raise ValueError(f"{filename}: tiene más de {MAX_ROWS} filas; divídelo en partes")
        parsed.append((filename, columns, data_rows))

    categories = CategoryIndex(db)
    products = db.query(Product).all()
    by_code = {p.code.upper(): p for p in products}
    by_name = {_fold(p.name): p for p in products}

    results: list[dict[str, Any]] = []
    counts = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    new_categories: list[str] = []
    current_file = ""

    def add(action: str, row: int, name: str, message: str = "") -> None:
        key = {"create": "created", "update": "updated", "skip": "skipped", "error": "errors"}[action]
        counts[key] += 1
        result = {"row": row, "action": action, "name": name, "message": message}
        if len(files) > 1:
            result["file"] = current_file
        results.append(result)

    rows_to_process = [
        (filename, columns, number, raw_row)
        for filename, columns, data_rows in parsed
        for number, raw_row in enumerate(data_rows, start=2)
    ]
    for current_file, columns, row_number, raw_row in rows_to_process:
        if not any(c.strip() for c in raw_row):
            continue

        values: dict[str, str] = {}
        for index, field in columns.items():
            if index < len(raw_row) and raw_row[index].strip():
                values[field] = raw_row[index].strip()

        name = values.get("name", "")
        if not name:
            add("error", row_number, "", "Falta el nombre")
            continue
        if _fold(name).startswith(EXAMPLE_PREFIX):
            add("skip", row_number, name, "Fila de ejemplo de la plantilla")
            continue

        # Convertir y validar celdas.
        try:
            fields: dict[str, Any] = {}
            for field, raw in values.items():
                if field in ("name", "category", "code"):
                    continue
                if field in _NUMERIC:
                    fields[field] = parse_number(raw)
                elif field in _INTEGER:
                    fields[field] = int(round(parse_number(raw)))
                elif field in _LISTS:
                    fields[field] = _split_list(raw)
                else:
                    fields[field] = raw
        except ValueError as exc:
            add("error", row_number, name, str(exc))
            continue

        category: Category | None = None
        if "category" in values:
            if create_categories:
                category, problem, created_now = categories.find_or_create(db, values["category"], dry_run)
                new_categories.extend(c for c in created_now if c not in new_categories)
            else:
                category, problem = categories.find(values["category"])
            if problem:
                add("error", row_number, name, problem)
                continue

        existing = None
        if "code" in values:
            existing = by_code.get(values["code"].upper())
            if existing is None:
                add("error", row_number, name, f"No existe un producto con el código {values['code']}")
                continue
        if existing is None:
            existing = by_name.get(_fold(name))

        try:
            if existing is not None:
                update = ProductUpdate(
                    **fields,
                    **({"category_id": category.id} if category else {}),
                    **({"name": name} if "code" in values else {}),
                )
                if not dry_run:
                    for key, value in update.model_dump(exclude_unset=True).items():
                        setattr(existing, key, value)
                add("update", row_number, existing.name, "Actualiza " + existing.code)
            else:
                if category is None:
                    add("error", row_number, name, "Falta la categoría (producto nuevo)")
                    continue
                no_price = "price" not in fields
                create = ProductCreate(category_id=category.id or 0, name=name, **fields)
                code = "(se asigna al importar)"
                if not dry_run:
                    code = next_code(db, resolve_code_prefix(category))
                    product = Product(code=code, created_by=user_id, **create.model_dump())
                    if no_price:
                        product.price_estimated = True
                    db.add(product)
                    by_name[_fold(name)] = product
                    by_code[code.upper()] = product
                else:
                    # Dos filas con el mismo nombre en el archivo: la segunda actualiza a la primera.
                    by_name[_fold(name)] = Product(code=code, name=name)
                add("create", row_number, name, f"Nuevo en {category.name}" + (" · sin precio: complétalo" if no_price else ""))
        except ValidationError as exc:
            detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            add("error", row_number, name, detail)

    if not dry_run:
        db.commit()

    return {
        "dry_run": dry_run,
        **counts,
        "ignored_columns": ignored,
        "new_categories": new_categories,
        "files": [name for name, _ in files],
        "rows": results[:500],
    }
