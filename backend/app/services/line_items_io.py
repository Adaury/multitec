"""Partidas de cotización / presupuesto desde y hacia una hoja de cálculo.

Descargar: las líneas de una cotización con las mismas columnas que se aceptan al subir, así se puede bajar,
corregir en Excel y volver a cargar. Subir: uno o varios archivos (CSV o Excel) con Código, Descripción,
Cantidad, Precio y Nota. Cada línea se busca en el catálogo por código o por nombre; si se encuentra, queda
enlazada al producto (y toma su precio cuando el archivo no lo trae).
"""

import re
import unicodedata
from typing import Any

from sqlalchemy.orm import Session

from app.models.product import Product
from app.services.catalog_import import parse_number
from app.services.spreadsheets import build_csv_semicolon, build_xlsx, read_rows

HEADERS = ["Codigo", "Descripcion", "Cantidad", "Unidad", "Precio", "Subtotal", "Nota"]
MAX_LINES = 500

_ALIASES = {
    "code": ["codigo", "code", "sku", "cod"],
    "description": ["descripcion", "producto", "nombre", "articulo", "item", "material", "detalle", "concepto"],
    "quantity": ["cantidad", "cant", "qty", "unidades", "cantidad_requerida"],
    "unit_price": ["precio", "precio_unitario", "precio_unit", "p_unit", "costo_unitario", "valor_unitario", "price"],
    "note": ["nota", "notas", "observacion", "observaciones", "comentario"],
}
_BY_HEADER = {alias: field for field, names in _ALIASES.items() for alias in names}


def _fold(text: str) -> str:
    stripped = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", stripped.lower()).strip()


def _key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", _fold(text)).strip("_")


def export_items(db: Session, quote, fmt: str) -> tuple[bytes, str]:
    ids = [i.product_id for i in quote.items if i.product_id]
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(ids)).all()} if ids else {}
    rows: list[list[Any]] = []
    for item in quote.items:
        product = products.get(item.product_id)
        code = product.code if product is not None else ""
        unit = product.unit if product is not None else ""
        rows.append([code, item.description, float(item.quantity), unit, float(item.unit_price), float(item.subtotal), item.note or ""])
    rows.append([])
    rows.append(["", "Subtotal", "", "", "", float(quote.subtotal), ""])
    rows.append(["", "ITBIS (18%)", "", "", "", float(quote.itbis), ""])
    rows.append(["", "TOTAL", "", "", "", float(quote.total), ""])
    name = f"{quote.code}-partidas"
    if fmt == "xlsx":
        return build_xlsx(HEADERS, rows, quote.code, [14, 46, 10, 10, 14, 14, 30]), f"{name}.xlsx"
    return build_csv_semicolon(HEADERS, rows), f"{name}.csv"


def template_items(fmt: str) -> tuple[bytes, str]:
    rows = [
        ["", "Cámara IP 4MP domo", 4, "unidad", "", "", "Una por esquina"],
        ["", "Sensor de movimiento PIR", 3, "unidad", "", "", ""],
        ["", "Taco plástico 1/4\" (bolsa 100)", 1, "bolsa", "", "", ""],
    ]
    if fmt == "xlsx":
        return build_xlsx(HEADERS, rows, "Partidas", [14, 46, 10, 10, 14, 14, 30]), "plantilla_partidas.xlsx"
    return build_csv_semicolon(HEADERS, rows), "plantilla_partidas.csv"


def parse_items(db: Session, files: list[tuple[str, bytes]]) -> dict[str, Any]:
    """Lee las partidas de los archivos. No guarda nada: la pantalla las agrega a la cotización que se edita."""
    products = db.query(Product).all()
    by_code = {p.code.upper(): p for p in products}
    by_name: dict[str, Product] = {}
    for p in products:
        by_name.setdefault(_fold(p.name), p)
        for synonym in p.synonyms or []:
            by_name.setdefault(_fold(synonym), p)

    items: list[dict[str, Any]] = []
    warnings: list[str] = []
    for filename, data in files:
        try:
            rows = read_rows(data, filename)
        except ValueError as exc:
            raise ValueError(f"{filename}: {exc}") from None
        header_at = next((i for i, r in enumerate(rows) if any(c.strip() for c in r)), None)
        if header_at is None:
            warnings.append(f"{filename}: está vacío")
            continue
        columns: dict[int, str] = {}
        for index, title in enumerate(rows[header_at]):
            field = _BY_HEADER.get(_key(title))
            if field and field not in columns.values():
                columns[index] = field
        if "description" not in columns.values() and "code" not in columns.values():
            raise ValueError(f"{filename}: falta la columna 'Descripcion' (o 'Codigo'). Usa la plantilla de partidas.")

        for number, raw in enumerate(rows[header_at + 1 :], start=header_at + 2):
            values = {field: raw[i].strip() for i, field in columns.items() if i < len(raw) and raw[i].strip()}
            if not values:
                continue
            description = values.get("description", "")
            # Las filas de totales de un archivo descargado (Subtotal, ITBIS, TOTAL) no son partidas.
            if not values.get("code") and _fold(description).startswith(("subtotal", "itbis", "total")):
                continue
            product = by_code.get(values.get("code", "").upper()) if values.get("code") else None
            if product is None and description:
                product = by_name.get(_fold(description))
            if not description and product is None:
                warnings.append(f"{filename}, fila {number}: no existe el código {values.get('code')}")
                continue
            try:
                quantity = parse_number(values["quantity"]) if "quantity" in values else 1.0
                price = parse_number(values["unit_price"]) if "unit_price" in values else None
            except ValueError as exc:
                warnings.append(f"{filename}, fila {number}: {exc}")
                continue
            if quantity <= 0:
                warnings.append(f"{filename}, fila {number}: cantidad 0 o negativa, se omitió")
                continue
            if price is None:
                price = float(product.price or 0) if product is not None else 0.0
                if product is None:
                    warnings.append(f"{filename}, fila {number}: «{description}» no está en el catálogo ni trae precio")
            items.append({
                "product_id": product.id if product is not None else None,
                "description": description or product.name,
                "quantity": quantity,
                "unit_price": round(price, 2),
                "note": values.get("note"),
            })
            if len(items) > MAX_LINES:
                raise ValueError(f"Hay más de {MAX_LINES} partidas; divide los archivos")
    return {"items": items, "warnings": warnings, "matched": sum(1 for i in items if i["product_id"])}
