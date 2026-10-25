from datetime import datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog

router = APIRouter(prefix="/api/audit", tags=["audit"])

admin_only = require_role("admin")


class AuditOut(BaseModel):
    id: int
    created_at: datetime
    user_id: int | None
    user_email: str | None
    action: str
    entity: str | None
    entity_id: int | None
    detail: str | None
    ip: str | None

    class Config:
        from_attributes = True


@router.get("", response_model=list[AuditOut])
def list_audit(
    action: str | None = None,
    user_id: int | None = None,
    before_id: int | None = Query(default=None, description="Para paginar: solo registros más antiguos que este id"),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(admin_only),
):
    """Solo el admin ve la bitácora. Los más recientes primero."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if before_id is not None:
        query = query.filter(AuditLog.id < before_id)
    return query.order_by(AuditLog.id.desc()).limit(limit).all()
