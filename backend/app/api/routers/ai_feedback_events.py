from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.ai_engine.learning_analysis import detect_accessory_candidates, detect_stale_rule_candidates
from app.core.security import require_role
from app.db.session import get_db
from app.models.ai_feedback_event import AIFeedbackEvent
from app.schemas.ai_feedback_event import AIFeedbackEventOut
from app.schemas.learning_analysis import AccessoryCandidateOut, LearningAnalysisOut, StaleRuleCandidateOut

router = APIRouter(prefix="/api/ai-feedback-events", tags=["ai-feedback-events"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


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


@router.post("/analyze", response_model=LearningAnalysisOut)
def analyze_ai_feedback_events(db: Session = Depends(get_db), _=Depends(admin_only)):
    """Dispara las dos consultas de detección de Motor 7 (§ "Scoping del análisis
    periódico", docs/ai-engine-architecture.md) bajo demanda — sin scheduler, igual que
    `quote_archiver.archive_stale_quotes` evita uno corriendo perezosamente. Es una
    lectura pesada (recorre todos los eventos), por eso es un botón que un admin dispara
    cuando quiere revisar candidatos, no algo automático. Los resultados son de solo
    lectura: no crea ni borra ninguna `TechnicalRule` por su cuenta."""
    return LearningAnalysisOut(
        accessory_candidates=[
            AccessoryCandidateOut.model_validate(c, from_attributes=True) for c in detect_accessory_candidates(db)
        ],
        stale_rule_candidates=[
            StaleRuleCandidateOut.model_validate(c, from_attributes=True) for c in detect_stale_rule_candidates(db)
        ],
    )
