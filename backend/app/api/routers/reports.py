from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.core.timeutil import today_dr
from app.db.session import get_db
from app.schemas.margin import MarginSummary
from app.schemas.reports import DashboardSummary
from app.schemas.timesheet import TimesheetOut
from app.services.timesheet import timesheet_csv_rows, timesheet_rows, timesheet_totals
from app.services.csv_export import build_csv
from app.core.config import get_settings
from app.services.dgii_606 import build_606_report, build_606_rows
from app.services.dgii_607 import build_607_consumption_summary, build_607_report, build_607_rows
from app.services.dgii_608 import build_608_report, build_608_rows
from app.services.dgii_txt import build_dgii_txt, company_rnc_digits
from app.services.margin import company_margin_last_months
from app.services.reports import dashboard_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return dashboard_summary(db)


@router.get("/dashboard/export")
def export_dashboard_csv(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    summary = dashboard_summary(db)
    rows = [["Cotizaciones pendientes", "", summary["quotes_pending"]]]
    rows.append(["Tickets abiertos", "", summary["open_tickets_total"]])
    for row in summary["projects_by_status"]:
        rows.append(["Proyectos por estado", row["status"], row["count"]])
    for row in summary["monthly_invoicing"]:
        rows.append(["Facturación mensual", row["month"], row["total"]])
    for row in summary["open_tickets_by_technician"]:
        rows.append(["Tickets por técnico", row["technician"], row["count"]])

    csv_bytes = build_csv(["Sección", "Etiqueta", "Valor"], rows)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="dashboard.csv"'},
    )


@router.get("/margin", response_model=MarginSummary)
def get_margin_report(db: Session = Depends(get_db), _=Depends(admin_only)):
    return company_margin_last_months(db)


def _timesheet_range(start: date | None, end: date | None) -> tuple[date, date]:
    """Por defecto, la semana en curso (lunes a hoy)."""
    today = today_dr()
    first = start or today - timedelta(days=today.weekday())
    last = end or today
    if last < first:
        raise HTTPException(status_code=400, detail="La fecha final no puede ser anterior a la inicial")
    if (last - first).days > 366:
        raise HTTPException(status_code=400, detail="El rango no puede pasar de un año")
    return first, last


@router.get("/timesheet", response_model=TimesheetOut)
def get_timesheet(
    start: date | None = None,
    end: date | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    """Horas en sitio por técnico, de la entrada y salida marcadas en cada visita."""
    first, last = _timesheet_range(start, end)
    rows = timesheet_rows(db, first, last, user_id)
    return {"start": first, "end": last, "rows": rows, "totals": timesheet_totals(rows)}


@router.get("/timesheet/export")
def export_timesheet_csv(
    start: date | None = None,
    end: date | None = None,
    user_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    first, last = _timesheet_range(start, end)
    rows = timesheet_rows(db, first, last, user_id)
    headers = ["Fecha", "Técnico", "Proyecto", "Cliente", "Entrada", "Salida", "Horas"]
    return Response(
        content=build_csv(headers, timesheet_csv_rows(rows)),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="hoja-de-tiempo-{first}-{last}.csv"'},
    )


def _dgii_response(form: str, year: int, month: int, fmt: str, csv_builder, rows_builder, db: Session) -> Response:
    """CSV (revisión en Excel) o TXT con el formato de envío de la DGII."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mes inválido, debe ser 1-12")
    if fmt == "txt":
        content = build_dgii_txt(form, get_settings().company_rnc, year, month, rows_builder(db, year, month))
        media_type = "text/plain"
    else:
        content, media_type = csv_builder(db, year, month), "text/csv"
    if fmt == "txt":
        # Nombre que usa la DGII para el archivo de envío: DGII_F_607_<RNC>_<AAAAMM>.TXT
        filename = f"DGII_F_{form}_{company_rnc_digits(get_settings().company_rnc)}_{year:04d}{month:02d}.TXT"
    else:
        filename = f"{form}_{year:04d}{month:02d}.csv"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/dgii-606")
def export_dgii_606(
    year: int, month: int, format: str = "csv", db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    return _dgii_response("606", year, month, format, build_606_report, build_606_rows, db)


@router.get("/dgii-608")
def export_dgii_608(
    year: int, month: int, format: str = "csv", db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    return _dgii_response("608", year, month, format, build_608_report, build_608_rows, db)


@router.get("/dgii-607/consumo-resumen")
def dgii_607_consumption_summary(year: int, month: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Cantidad y monto de las facturas de consumo menores de RD$250,000 del mes: no van en el
    detalle del 607, se digitan en el resumen de la Oficina Virtual."""
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mes inválido, debe ser 1-12")
    return build_607_consumption_summary(db, year, month)


@router.get("/dgii-607")
def export_dgii_607(
    year: int, month: int, format: str = "csv", db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    return _dgii_response("607", year, month, format, build_607_report, build_607_rows, db)
