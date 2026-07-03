from sqlalchemy.orm import Session, joinedload

from app.models.invoice import Invoice
from app.models.project import Project
from app.services.csv_export import build_csv

# 01 = Ingresos por operaciones (régimen ordinario) — único tipo de ingreso que maneja
# este negocio (instalación/servicios), no hay ingresos financieros/extraordinarios/etc.
INCOME_TYPE_SERVICES = "01"

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
    sistema sabe con certeza: NCF, RNC del cliente, fecha, monto facturado e ITBIS. No
    trackeamos forma de pago (efectivo/tarjeta/crédito/etc.) ni retenciones, así que esas
    columnas quedan vacías — hay que completarlas a mano si aplican antes de enviar a la
    DGII. Verificar las columnas contra la plantilla oficial vigente antes de remitir."""
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.project).joinedload(Project.client))
        .order_by(Invoice.created_at)
        .all()
    )
    period_invoices = [inv for inv in invoices if inv.created_at.year == year and inv.created_at.month == month]

    rows = []
    for inv in period_invoices:
        client = inv.project.client
        rows.append(
            [
                client.rnc or "",
                _identification_type(client.rnc),
                inv.ncf or "",
                "",
                INCOME_TYPE_SERVICES,
                inv.created_at.strftime("%Y%m%d"),
                "",
                float(inv.subtotal),
                float(inv.itbis),
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            ]
        )

    return build_csv(REPORT_607_HEADERS, rows)
