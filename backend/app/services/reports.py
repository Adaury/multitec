from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote
from app.models.ticket import Ticket
from app.models.user import User

OPEN_TICKET_STATUSES = ("abierto", "en_proceso")


def _last_n_months(n: int) -> list[str]:
    today = date.today()
    year, month = today.year, today.month
    months = []
    for _ in range(n):
        months.append(f"{year:04d}-{month:02d}")
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return list(reversed(months))


def dashboard_summary(db: Session) -> dict:
    projects_by_status = db.query(Project.status, func.count(Project.id)).group_by(Project.status).all()

    months = _last_n_months(6)
    range_start = date(int(months[0][:4]), int(months[0][5:7]), 1)
    monthly_totals = {m: 0.0 for m in months}
    for created_at, total in db.query(Invoice.created_at, Invoice.total).filter(Invoice.created_at >= range_start):
        key = f"{created_at.year:04d}-{created_at.month:02d}"
        if key in monthly_totals:
            monthly_totals[key] += float(total)

    quotes_pending = db.query(func.count(Quote.id)).filter(Quote.status == "pendiente").scalar() or 0

    ticket_rows = (
        db.query(Ticket.technician_id, func.count(Ticket.id))
        .filter(Ticket.status.in_(OPEN_TICKET_STATUSES))
        .group_by(Ticket.technician_id)
        .all()
    )
    technician_ids = [tid for tid, _ in ticket_rows if tid is not None]
    technician_names = {
        u.id: u.name for u in db.query(User).filter(User.id.in_(technician_ids))
    } if technician_ids else {}

    return {
        "projects_by_status": [{"status": status, "count": count} for status, count in projects_by_status],
        "monthly_invoicing": [{"month": m, "total": round(monthly_totals[m], 2)} for m in months],
        "quotes_pending": quotes_pending,
        "open_tickets_by_technician": [
            {"technician": technician_names.get(tid, "Sin asignar") if tid is not None else "Sin asignar", "count": count}
            for tid, count in ticket_rows
        ],
        "open_tickets_total": sum(count for _, count in ticket_rows),
    }
