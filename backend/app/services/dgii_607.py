from sqlalchemy.orm import Session, joinedload

from app.core.timeutil import to_local
from app.models.invoice import Invoice
from app.models.project import Project
from app.services.csv_export import build_csv

# 01 = Ingresos por operaciones (régimen ordinario) — único tipo de ingreso que maneja
# este negocio (instalación/servicios), no hay ingresos financieros/extraordinarios/etc.
INCOME_TYPE_SERVICES = "01"

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
    "ITBIS Retenido",
    "ITBIS Sujeto a Proporcionalidad",
    "ITBIS Percibido por Terceros",
    "Retención Renta por Terceros",
    "ISC",
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
    """1 = RNC (persona jurídica, 9 dígitos), 2 = Cédula (persona física, 11 dígitos),
    3 = no identificado (consumidor final sin RNC/cédula registrado)."""
    if not rnc:
        return "3"
    digits = "".join(ch for ch in rnc if ch.isdigit())
    return "2" if len(digits) == 11 else "1"


def build_607_report(db: Session, year: int, month: int) -> bytes:
    """Reporte de Ventas (formato 607 de la DGII) para un período. Cubre lo que este
    sistema sabe con certeza: NCF, RNC del cliente, fecha, monto facturado e ITBIS, y — si se
    registraron en la factura — la forma de pago (en su columna, con el total cobrado) y las
    retenciones de ITBIS y renta con su fecha. Lo que no se registró queda vacío: hay que
    completarlo a mano antes de enviar a la DGII. Verificar las columnas contra la plantilla
    oficial vigente antes de remitir."""
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.project).joinedload(Project.client))
        .order_by(Invoice.created_at)
        .all()
    )
    period_invoices = []
    for inv in invoices:
        issued = to_local(inv.created_at)
        if issued.year == year and issued.month == month:
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
                row[12] = isr_withheld
        # La forma de pago va en su columna con el total cobrado (monto facturado + ITBIS).
        column = PAYMENT_COLUMN.get(inv.payment_method or "")
        if column is not None:
            row[column] = float(inv.total)
        rows.append(row)

    return build_csv(REPORT_607_HEADERS, rows)
