from datetime import date
from typing import Protocol, Sequence

from sqlalchemy.orm import Session

from app.models.invoice import Invoice, InvoiceItem
from app.models.product import Product
from app.models.quote import Quote, QuoteItem

EMPTY_MARGIN = {
    "revenue": 0.0,
    "cost": 0.0,
    "margin": 0.0,
    "margin_pct": None,
    "lines_total": 0,
    "lines_costed": 0,
    "basis": "ninguno",
}


class MarginLine(Protocol):
    product_id: int | None
    quantity: float
    subtotal: float


def compute_margin(db: Session, items: Sequence[MarginLine], basis: str) -> dict:
    """Costo/margen de un conjunto de líneas (QuoteItem/InvoiceItem), cruzando cada una
    contra el `Product.cost` *actual* del catálogo — no hay snapshot de costo por línea,
    así que el margen de documentos viejos se recalcula con el costo de hoy (ver plan de
    rentabilidad, "sin snapshot"). Una línea sin `product_id`, o cuyo producto no tiene
    costo cargado (`cost == 0`), aporta a `revenue` pero no a `cost`: se cuenta en
    `lines_total` sin sumar a `lines_costed`, para que el consumidor pueda advertir que el
    margen es parcial."""
    product_ids = {item.product_id for item in items if item.product_id is not None}
    costs_by_id: dict[int, float] = {}
    if product_ids:
        costs_by_id = {
            row.id: float(row.cost)
            for row in db.query(Product.id, Product.cost).filter(Product.id.in_(product_ids))
        }

    revenue = 0.0
    cost = 0.0
    lines_total = 0
    lines_costed = 0
    for item in items:
        lines_total += 1
        revenue += float(item.subtotal)
        unit_cost = costs_by_id.get(item.product_id) if item.product_id is not None else None
        if unit_cost:
            cost += float(item.quantity) * unit_cost
            lines_costed += 1

    revenue = round(revenue, 2)
    cost = round(cost, 2)
    margin = round(revenue - cost, 2)
    margin_pct = round(margin / revenue, 4) if revenue else None

    return {
        "revenue": revenue,
        "cost": cost,
        "margin": margin,
        "margin_pct": margin_pct,
        "lines_total": lines_total,
        "lines_costed": lines_costed,
        "basis": basis,
    }


def project_margin(db: Session, project_id: int) -> dict:
    """Margen de un proyecto: prioriza lo realmente facturado (`basis='facturado'`); si
    todavía no hay facturas, cae a un margen *proyectado* sobre las líneas de sus
    cotizaciones aprobadas (`basis='cotizado'`, lo que se espera facturar); si no hay
    ninguna de las dos, devuelve ceros con `basis='ninguno'`."""
    invoice_items = db.query(InvoiceItem).join(Invoice).filter(Invoice.project_id == project_id).all()
    if invoice_items:
        return compute_margin(db, invoice_items, basis="facturado")

    quote_items = (
        db.query(QuoteItem)
        .join(Quote)
        .filter(Quote.project_id == project_id, Quote.status == "aprobada")
        .all()
    )
    if quote_items:
        return compute_margin(db, quote_items, basis="cotizado")

    return dict(EMPTY_MARGIN)


def company_margin_last_months(db: Session, months: int = 6) -> dict:
    """Margen agregado de la empresa sobre líneas de factura de los últimos `months`
    meses (mismo rango que `dashboard_summary`/`monthly_invoicing` en `services/reports.py`)."""
    today = date.today()
    year, month = today.year, today.month
    for _ in range(months - 1):
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    range_start = date(year, month, 1)

    items = db.query(InvoiceItem).join(Invoice).filter(Invoice.created_at >= range_start).all()
    return compute_margin(db, items, basis="facturado")
