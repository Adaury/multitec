from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.material import Material
from app.models.quote import Quote, QuoteHistory


def mark_quote_approved(db: Session, quote: Quote, created_by: int | None, note: str | None = None) -> None:
    """Aprueba la cotización y genera la lista de materiales (§18) a partir de sus
    líneas, una sola vez por cotización aunque se re-apruebe tras reactivar. No hace
    commit — el caller decide cuándo."""
    quote.status = "aprobada"
    quote.decided_at = datetime.now(timezone.utc)
    db.add(QuoteHistory(quote_id=quote.id, action="aprobada", note=note))

    already_generated = db.query(Material).filter(Material.source_quote_id == quote.id).first() is not None
    if not already_generated:
        for item in quote.items:
            db.add(
                Material(
                    project_id=quote.project_id,
                    product_id=item.product_id,
                    source_quote_id=quote.id,
                    description=item.description,
                    quantity=item.quantity,
                    status="pendiente_compra",
                    created_by=created_by,
                )
            )
