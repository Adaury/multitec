from sqlalchemy.orm import Session, joinedload

from app.models.purchase_invoice import PurchaseInvoice
from app.services.csv_export import build_csv

REPORT_606_HEADERS = [
    "RNC/Cédula Proveedor",
    "Tipo Identificación",
    "Tipo de Bienes y Servicios Comprados",
    "NCF",
    "NCF Modificado",
    "Fecha Comprobante",
    "Fecha Pago",
    "Monto Facturado en Servicios",
    "Monto Facturado en Bienes",
    "Total Monto Facturado",
    "ITBIS Facturado",
    "ITBIS Retenido",
    "ITBIS sujeto a Proporcionalidad",
    "ITBIS llevado al Costo",
    "ITBIS por Adelantar",
    "ITBIS percibido en compras",
    "Tipo de Retención en ISR",
    "Monto Retención Renta",
    "ISR Percibido en compras",
    "Impuesto Selectivo al Consumo",
    "Otros Impuestos/Tasas",
    "Monto Propina Legal",
    "Forma de Pago",
]


def _identification_type(rnc: str | None) -> str:
    """1 = RNC (9 dígitos), 2 = Cédula (11 dígitos). En compras el proveedor siempre debe
    estar identificado, así que no existe el "3" del 607."""
    digits = "".join(ch for ch in (rnc or "") if ch.isdigit())
    return "2" if len(digits) == 11 else "1"


def build_606_report(db: Session, year: int, month: int) -> bytes:
    """Reporte de Compras (formato 606 de la DGII) para un período, según la fecha del
    comprobante. Cubre lo que el sistema registra: NCF, proveedor, montos, ITBIS y
    retenciones capturadas a mano. Proporcionalidad, ITBIS al costo, percepciones, ISC,
    otros impuestos y propina quedan vacíos. El ITBIS facturado se reporta completo como
    "por adelantar". Verificar contra la plantilla oficial vigente antes de remitir."""
    invoices = (
        db.query(PurchaseInvoice)
        .options(joinedload(PurchaseInvoice.supplier))
        .order_by(PurchaseInvoice.invoice_date, PurchaseInvoice.id)
        .all()
    )
    rows = []
    for inv in invoices:
        if inv.invoice_date.year != year or inv.invoice_date.month != month:
            continue
        services = float(inv.services_amount)
        goods = float(inv.goods_amount)
        itbis = float(inv.itbis_invoiced)
        rows.append(
            [
                inv.supplier.rnc or "",
                _identification_type(inv.supplier.rnc),
                inv.expense_type,
                inv.ncf,
                inv.ncf_modified or "",
                inv.invoice_date.strftime("%Y%m%d"),
                inv.payment_date.strftime("%Y%m%d") if inv.payment_date else "",
                services,
                goods,
                services + goods,
                itbis,
                float(inv.itbis_withheld) or "",
                "",
                "",
                itbis,
                "",
                "",
                float(inv.isr_withheld) or "",
                "",
                "",
                "",
                "",
                inv.payment_type,
            ]
        )
    return build_csv(REPORT_606_HEADERS, rows)
