from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.product import Product


def resolve_item_fields(
    db: Session, product_id: int | None, description: str, unit_price: float | None
) -> tuple[str, float]:
    """Completa descripción/precio de una línea de presupuesto/cotización/factura desde el
    catálogo cuando falta. `unit_price=None` significa "no lo mandó el caller" (usar el
    precio del catálogo si hay product_id, o 0 si es una línea de texto libre) — distinto
    de un $0 explícito, que se respeta tal cual (ej. un artículo de regalo/garantía)."""
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Producto {product_id} no encontrado")
        description = description or product.name
        if unit_price is None:
            unit_price = float(product.price)
    elif unit_price is None:
        unit_price = 0.0
    return description, unit_price
