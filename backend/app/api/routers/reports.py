from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.schemas.reports import DashboardSummary
from app.services.reports import dashboard_summary

router = APIRouter(prefix="/api/reports", tags=["reports"])

allowed_roles = require_role("admin", "oficina")


@router.get("/dashboard", response_model=DashboardSummary)
def get_dashboard_summary(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return dashboard_summary(db)
