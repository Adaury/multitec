from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.schemas.followup import FollowupsOut
from app.services.followups import build_followups

router = APIRouter(prefix="/api/followups", tags=["followups"])

# Dinero por cobrar: el técnico no lo ve (igual que facturas y cotizaciones).
allowed_roles = require_role("admin", "oficina")


@router.get("", response_model=FollowupsOut)
def get_followups(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Facturas por cobrar y cotizaciones sin respuesta, con el mensaje de seguimiento ya redactado.
    Solo lectura: no envía nada, el usuario decide si manda el mensaje."""
    return build_followups(db)
