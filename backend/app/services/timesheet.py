"""Hoja de tiempo: las horas que cada técnico estuvo en el sitio, sacadas de la entrada y salida que marca en
cada visita (no se teclean a mano). Una visita sin salida aparece con minutos vacíos: sigue en curso o se
olvidó marcar."""

from datetime import date

from sqlalchemy.orm import Session, joinedload

from app.core.timeutil import to_local
from app.models.project import Project
from app.models.visit import Visit


def timesheet_rows(db: Session, start: date, end: date, user_id: int | None = None) -> list[dict]:
    query = (
        db.query(Visit)
        .options(joinedload(Visit.project).joinedload(Project.client), joinedload(Visit.technician))
        .filter(
            Visit.scheduled_date >= start,
            Visit.scheduled_date <= end,
            Visit.checkin_at.is_not(None),
            Visit.status != "cancelada",
        )
    )
    if user_id is not None:
        query = query.filter(Visit.technician_id == user_id)
    visits = query.order_by(Visit.scheduled_date, Visit.checkin_at).all()
    return [
        {
            "visit_id": v.id,
            "date": v.scheduled_date,
            "technician_id": v.technician_id,
            "technician": v.technician.name if v.technician else "Sin asignar",
            "project_code": v.project.code,
            "client_name": v.project.client.name,
            "checkin_at": v.checkin_at,
            "checkout_at": v.checkout_at,
            "minutes": v.minutes_on_site,
        }
        for v in visits
    ]


def timesheet_totals(rows: list[dict]) -> list[dict]:
    """Total por técnico (solo las visitas con entrada y salida cuentan para las horas)."""
    totals: dict[tuple, dict] = {}
    for row in rows:
        entry = totals.setdefault(
            (row["technician_id"], row["technician"]),
            {"technician_id": row["technician_id"], "technician": row["technician"], "visits": 0, "minutes": 0, "open": 0},
        )
        entry["visits"] += 1
        if row["minutes"] is None:
            entry["open"] += 1
        else:
            entry["minutes"] += row["minutes"]
    return sorted(totals.values(), key=lambda t: t["technician"])


def timesheet_csv_rows(rows: list[dict]) -> list[list]:
    out = []
    for r in rows:
        out.append(
            [
                r["date"].isoformat(),
                r["technician"],
                r["project_code"],
                r["client_name"],
                to_local(r["checkin_at"]).strftime("%H:%M") if r["checkin_at"] else "",
                to_local(r["checkout_at"]).strftime("%H:%M") if r["checkout_at"] else "",
                round(r["minutes"] / 60, 2) if r["minutes"] is not None else "",
            ]
        )
    return out
