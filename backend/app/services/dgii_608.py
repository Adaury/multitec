from sqlalchemy.orm import Session

from app.core.timeutil import to_local
from app.models.invoice import VOID_REASONS, Invoice
from app.services.csv_export import build_csv

REPORT_608_HEADERS = [
    "Número de Comprobante Fiscal",
    "Fecha de Comprobante",
    "Tipo de Anulación",
    "Descripción del Tipo de Anulación",
]


def build_608_rows(db: Session, year: int, month: int) -> list[list]:
    """Comprobantes anulados en el período (según la fecha de anulación): NCF, fecha en que se
    emitió y tipo de anulación. Solo cubre facturas anuladas desde el sistema; un NCF que nunca
    se llegó a usar (hoja dañada, salto de secuencia) hay que sumarlo a mano antes de enviar."""
    voided = db.query(Invoice).filter(Invoice.voided_at.is_not(None)).order_by(Invoice.voided_at, Invoice.id).all()
    rows = []
    for inv in voided:
        when = to_local(inv.voided_at)
        if when.year != year or when.month != month or not inv.ncf:
            continue
        rows.append([inv.ncf, to_local(inv.created_at).strftime("%Y%m%d"), inv.void_reason or ""])
    return rows


def build_608_report(db: Session, year: int, month: int) -> bytes:
    rows = [
        [ncf, date, code, VOID_REASONS.get(code, "")] for ncf, date, code in build_608_rows(db, year, month)
    ]
    return build_csv(REPORT_608_HEADERS, rows)
