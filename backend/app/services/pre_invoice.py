from sqlalchemy.orm import Session

from app.models.invoice import PreInvoice, PreInvoiceItem
from app.models.quote import Quote
from app.services.code_generator import next_code


def build_pre_invoice_from_quote(db: Session, quote: Quote, created_by: int | None) -> PreInvoice:
    """Copia una cotización aprobada a una prefactura (sin recalcular — mismos totales e
    items verbatim) sin comitear; el caller decide cuándo. Idempotente por
    `source_quote_id`: si ya existe una prefactura para esta cotización, la devuelve en
    vez de duplicarla — necesario porque esto se llama tanto desde la generación manual
    (invoices.py) como automáticamente al aprobar la cotización (quote_approval.py), y una
    cotización puede re-aprobarse tras reactivarse."""
    existing = db.query(PreInvoice).filter(PreInvoice.source_quote_id == quote.id).one_or_none()
    if existing is not None:
        return existing

    pre_invoice = PreInvoice(
        code=next_code(db, "PFC"),
        project_id=quote.project_id,
        source_quote_id=quote.id,
        notes=quote.notes,
        subtotal=quote.subtotal,
        itbis=quote.itbis,
        total=quote.total,
        created_by=created_by,
    )
    for item in quote.items:
        pre_invoice.items.append(
            PreInvoiceItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=item.subtotal,
            )
        )

    db.add(pre_invoice)
    return pre_invoice
