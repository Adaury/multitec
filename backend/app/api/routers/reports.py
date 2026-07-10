from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.schemas.margin import MarginSummary
from app.schemas.reports import DashboardSummary
from app.services.csv_export import build_csv
from app.services.dgii_607 import build_607_report
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


@router.get("/dgii-607")
def export_dgii_607(year: int, month: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    if not (1 <= month <= 12):
        raise HTTPException(status_code=400, detail="Mes inválido, debe ser 1-12")
    csv_bytes = build_607_report(db, year, month)
    filename = f"607_{year:04d}{month:02d}.csv"
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
