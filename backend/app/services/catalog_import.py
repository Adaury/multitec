"""Importación masiva de productos del catálogo desde un CSV (el que genera Excel con "Guardar como
CSV"). Pensado para cargar de golpe una lista de precios en vez de crear producto por producto.

Reglas, a propósito conservadoras:
  * Una celda vacía NUNCA borra un dato que el producto ya tiene: solo se actualiza lo que viene lleno.
  * Se reconoce un producto existente por su `codigo` o, si no viene, por su nombre (sin importar
    mayúsculas ni tildes); si existe se actualiza, si no se crea.
  * Un producto nuevo necesita categoría. La categoría se busca por nombre ("Cámaras IP") o por
    ruta ("CCTV > Cámaras IP"); si el nombre existe en varias ramas se pide la ruta.
  * Las filas con error no frenan al resto: se informan una por una.
  * `dry_run=True` calcula y devuelve el mismo resumen sin tocar la base de datos.
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
    "priority": ["prioridad", "priority"],
    "code": ["codigo", "code", "sku"],
}.items():
    for _n in _names:
        _ALIASES[_n] = _field

_NUMERIC = {"price", "cost", "install_minutes", "resolution_mp", "storage_capacity_gb"}
_INTEGER = {"channel_capacity", "priority"}
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


class CategoryIndex:
    def __init__(self, db: Session):
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


def import_catalog(db: Session, data: bytes, user_id: int | None, dry_run: bool) -> dict[str, Any]:
    if len(data) > MAX_BYTES:
        raise ValueError(f"El archivo pesa más de {MAX_BYTES // (1024 * 1024)} MB")
    text = _decode(data)
    lines = text.splitlines()
    delimiter = None
    if lines and lines[0].strip().lower().startswith("sep=") and len(lines[0].strip()) >= 5:
        delimiter = lines[0].strip()[4]
        text = "\n".join(lines[1:])
        lines = lines[1:]
    if not any(line.strip() for line in lines):
        raise ValueError("El archivo está vacío")
    if delimiter is None:
        first = next(line for line in lines if line.strip())
        delimiter = max([";", ",", "\t"], key=first.count)

    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    try:
        header_row = next(r for r in reader if any(c.strip() for c in r))
    except StopIteration:
        raise ValueError("El archivo está vacío") from None

    columns: dict[int, str] = {}
    ignored: list[str] = []
    for index, title in enumerate(header_row):
        field = _ALIASES.get(_header_key(title))
        if field and field not in columns.values():
            columns[index] = field
        elif title.strip():
            ignored.append(title.strip())
    if "name" not in columns.values():
        raise ValueError("Falta la columna 'Nombre' (o 'Producto'). Usa la plantilla para empezar.")

    categories = CategoryIndex(db)
    products = db.query(Product).all()
    by_code = {p.code.upper(): p for p in products}
    by_name = {_fold(p.name): p for p in products}

    results: list[dict[str, Any]] = []
    counts = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}

    def add(action: str, row: int, name: str, message: str = "") -> None:
        key = {"create": "created", "update": "updated", "skip": "skipped", "error": "errors"}[action]
        counts[key] += 1
        results.append({"row": row, "action": action, "name": name, "message": message})

    row_number = 1  # la fila del encabezado
    for raw_row in reader:
        row_number += 1
        if not any(c.strip() for c in raw_row):
            continue
        if row_number - 1 > MAX_ROWS:
            raise ValueError(f"El archivo tiene más de {MAX_ROWS} filas; divídelo en partes")

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
                create = ProductCreate(category_id=category.id, name=name, **fields)
                code = "(se asigna al importar)"
                if not dry_run:
                    code = next_code(db, resolve_code_prefix(category))
                    product = Product(code=code, created_by=user_id, **create.model_dump())
                    db.add(product)
                    by_name[_fold(name)] = product
                    by_code[code.upper()] = product
                else:
                    # Dos filas con el mismo nombre en el archivo: la segunda actualiza a la primera.
                    by_name[_fold(name)] = Product(code=code, name=name)
                add("create", row_number, name, f"Nuevo en {category.name}")
        except ValidationError as exc:
            detail = "; ".join(f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors())
            add("error", row_number, name, detail)

    if not dry_run:
        db.commit()

    return {"dry_run": dry_run, **counts, "ignored_columns": ignored, "rows": results[:500]}
