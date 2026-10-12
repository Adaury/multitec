from sqlalchemy.orm import Session, joinedload

from app.core.timeutil import to_local
from app.models.invoice import Invoice
from app.models.project import Project
from app.services.csv_export import build_csv

# 01 = Ingresos por operaciones (régimen ordinario) — único tipo de ingreso que maneja
# este negocio (instalación/servicios), no hay ingresos financieros/extraordinarios/etc.
INCOME_TYPE_SERVICES = "01"

# Norma General 10-18: las facturas de consumo (B02) solo se detallan en el 607 si su valor es igual
# o mayor a este monto; las menores se declaran en el "Resumen General de Facturas de Consumo" que
# se digita en la Oficina Virtual al enviar el archivo.
CONSUMPTION_DETAIL_THRESHOLD = 250_000.00
CONSUMPTION_NCF_TYPE = "B02"

# Forma de pago -> posición de su columna en REPORT_607_HEADERS (Efectivo ... Otras Formas de Venta).
PAYMENT_COLUMN = {
    "efectivo": 16,
    "cheque_transferencia": 17,
    "tarjeta": 18,
    "credito": 19,
    "bonos": 20,
    "permuta": 21,
    "otras": 22,
}

REPORT_607_HEADERS = [
    "RNC/Cédula Comprador",
    "Tipo Identificación",
    "NCF",
    "NCF Modificado",
    "Tipo de Ingreso",
    "Fecha Comprobante",
    "Fecha Retención",
    "Monto Facturado",
    "ITBIS Facturado",
    "ITBIS Retenido por Terceros",
    "ITBIS Percibido",
    "Retención Renta por Terceros",
    "ISR Percibido",
    "Impuesto Selectivo al Consumo",
    "Otros Impuestos/Tasas",
    "Monto Propina Legal",
    "Efectivo",
    "Cheque/Transferencia/Depósito",
    "Tarjeta Débito/Crédito",
    "Venta a Crédito",
    "Bonos o Certificados de Regalo",
    "Permuta",
    "Otras Formas de Venta",
]


def _identification_type(rnc: str | None) -> str:
    """1 = RNC (9 dígitos), 2 = Cédula (11 dígitos). El 3 de la DGII es pasaporte / ID tributaria:
    no se infiere. Sin documento queda en blanco (solo ocurre en consumo de RD$250,000 o más)."""
    if not rnc:
        return ""
    digits = "".join(ch for ch in rnc if ch.isdigit())
    return "2" if len(digits) == 11 else "1"


def _is_summarized_consumption(inv: Invoice) -> bool:
    return inv.ncf_type == CONSUMPTION_NCF_TYPE and float(inv.total) < CONSUMPTION_DETAIL_THRESHOLD


def build_607_consumption_summary(db: Session, year: int, month: int) -> dict:
    """Lo que se digita en el "Resumen General de Facturas de Consumo" de la Oficina Virtual:
    cantidad de NCF de consumo del período (menores de RD$250,000) y su monto facturado."""
    count = 0
    subtotal = 0.0
    total = 0.0
    active_invoices = db.query(Invoice).filter(Invoice.voided_at.is_(None)).all()
    for inv in active_invoices:
        issued = to_local(inv.created_at)
        if issued.year == year and issued.month == month and _is_summarized_consumption(inv):
            count += 1
            subtotal += float(inv.subtotal)
            total += float(inv.total)
    return {"count": count, "subtotal": round(subtotal, 2), "total": round(total, 2)}


def build_607_rows(db: Session, year: int, month: int) -> list[list]:
    """Reporte de Ventas (formato 607 de la DGII) para un período. Cubre lo que este
    sistema sabe con certeza: NCF, RNC del cliente, fecha, monto facturado e ITBIS, y — si se
    registraron en la factura — la forma de pago (en su columna, con el total cobrado) y las
    retenciones de ITBIS y renta con su fecha. Lo que no se registró queda vacío: hay que
    completarlo a mano antes de enviar a la DGII. Verificar las columnas contra la plantilla
    oficial vigente antes de remitir."""
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.project).joinedload(Project.client))
        .filter(Invoice.voided_at.is_(None))  # las anuladas van en el 608, no en el 607
        .order_by(Invoice.created_at)
        .all()
    )
    period_invoices = []
    for inv in invoices:
        issued = to_local(inv.created_at)
        if issued.year == year and issued.month == month and not _is_summarized_consumption(inv):
            period_invoices.append((inv, issued))

    rows = []
    for inv, issued in period_invoices:
        client = inv.project.client
        itbis_withheld = float(inv.itbis_withheld or 0)
        isr_withheld = float(inv.isr_withheld or 0)
        has_retention = itbis_withheld > 0 or isr_withheld > 0
        row = [""] * len(REPORT_607_HEADERS)
        row[0] = client.rnc or ""
        row[1] = _identification_type(client.rnc)
        row[2] = inv.ncf or ""
        row[4] = INCOME_TYPE_SERVICES
        row[5] = issued.strftime("%Y%m%d")
        row[7] = float(inv.subtotal)
        row[8] = float(inv.itbis)
        if has_retention:
            if inv.retention_date:
                row[6] = inv.retention_date.strftime("%Y%m%d")
            if itbis_withheld > 0:
                row[9] = itbis_withheld
            if isr_withheld > 0:
                row[11] = isr_withheld  # "Retención Renta por Terceros" (col. 12); la 13 es ISR percibido
        # La forma de pago va en su columna con el total cobrado (monto facturado + ITBIS).
        column = PAYMENT_COLUMN.get(inv.payment_method or "")
        if column is not None:
            row[column] = float(inv.total)
        rows.append(row)

    return rows


def build_607_report(db: Session, year: int, month: int) -> bytes:
    return build_csv(REPORT_607_HEADERS, build_607_rows(db, year, month))
