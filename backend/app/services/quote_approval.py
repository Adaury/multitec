from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.material import Material
from app.models.quote import Quote, QuoteHistory
from app.services.pre_invoice import build_pre_invoice_from_quote


def build_material_rows_from_quote(quote: Quote) -> list[dict]:
    """Las líneas que `mark_quote_approved` convertirá en `Material` si esta cotización se
    aprueba. Factorizado aparte (en vez de inline en `mark_quote_approved`) para que la
    vista previa de lista de compras (§ Motor 6, `GET /api/quotes/{id}/purchase-list-preview`)
    nunca pueda divergir de lo que realmente se crea al aprobar — ambas leen de aquí."""
    return [
        {"product_id": item.product_id, "description": item.description, "quantity": float(item.quantity)}
        for item in quote.items
    ]


def mark_quote_approved(db: Session, quote: Quote, created_by: int | None, note: str | None = None) -> None:
    """Aprueba la cotización, genera la lista de materiales (§18) y la prefactura a partir
    de sus líneas — ambas idempotentes (una sola vez por cotización aunque se re-apruebe
    tras reactivar). No hace commit — el caller decide cuándo.

    La prefactura se genera aquí (no solo cuando alguien la pide a mano) porque copiar
    datos de una cotización ya aprobada no es una decisión de negocio nueva — es el mismo
    dato, sin juicio adicional; § levantamiento inteligente. El paso que sí sigue siendo
    manual y admin-only es convertir esa prefactura en factura con NCF real."""
    quote.status = "aprobada"
    quote.decided_at = datetime.now(timezone.utc)
    db.add(QuoteHistory(quote_id=quote.id, action="aprobada", note=note))

    already_generated = db.query(Material).filter(Material.source_quote_id == quote.id).first() is not None
    if not already_generated:
        for row in build_material_rows_from_quote(quote):
            db.add(
                Material(
                    project_id=quote.project_id,
                    source_quote_id=quote.id,
                    status="pendiente_compra",
                    created_by=created_by,
                    **row,
                )
            )

    build_pre_invoice_from_quote(db, quote, created_by)
