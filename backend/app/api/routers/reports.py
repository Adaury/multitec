from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.schemas.reports import DashboardSummary
from app.services.csv_export import build_csv
from app.services.reports import dashboard_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])

allowed_roles = require_role("admin", "oficina")


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
