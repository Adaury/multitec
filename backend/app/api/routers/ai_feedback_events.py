from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.ai_feedback_event import AIFeedbackEvent
from app.schemas.ai_feedback_event import AIFeedbackEventOut

router = APIRouter(prefix="/api/ai-feedback-events", tags=["ai-feedback-events"])

allowed_roles = require_role("admin", "oficina")


@router.get("", response_model=list[AIFeedbackEventOut])
def list_ai_feedback_events(
    project_id: int | None = None, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    """Solo lectura (§ Motor 7) — la captura pasiva de ediciones sobre Budget/Engineering
    generados por IA. No hay create/update/delete: estas filas las escribe el sistema en
    app.ai_engine.learning, nunca un usuario. Sin análisis todavía sobre estos datos — ver
    docs/ai-engine-architecture.md."""
    query = db.query(AIFeedbackEvent)
    if project_id is not None:
        query = query.filter(AIFeedbackEvent.project_id == project_id)
    return query.order_by(AIFeedbackEvent.created_at.desc()).all()
