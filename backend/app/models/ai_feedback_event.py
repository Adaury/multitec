from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ENTITY_TYPE_BUDGET_ITEM = "budget_item"
ENTITY_TYPE_ENGINEERING = "engineering"
ENTITY_TYPES = (ENTITY_TYPE_BUDGET_ITEM, ENTITY_TYPE_ENGINEERING)

# "ai_suggested" queda declarado para completar el dominio del campo (§ diseño de Motor 7)
# aunque hoy nada escribe ese origin — solo se registran los tres tipos de corrección
# humana, que es la señal que hay que capturar. Ver app.ai_engine.learning.
ORIGIN_HUMAN_ADDED = "human_added"
ORIGIN_HUMAN_REMOVED = "human_removed"
ORIGIN_HUMAN_MODIFIED = "human_modified"
ORIGINS = ("ai_suggested", ORIGIN_HUMAN_ADDED, ORIGIN_HUMAN_REMOVED, ORIGIN_HUMAN_MODIFIED)


class AIFeedbackEvent(Base):
    """Captura pasiva de Motor 7 (§ docs/ai-engine-architecture.md) — qué corrigió un
    humano sobre algo que la IA generó. Se escribe automáticamente al editar un `Budget` o
    una `Engineering` que todavía tenían `ai_generated=True` (ver
    `app.ai_engine.learning`); nada lee ni actúa sobre estas filas todavía — el análisis
    periódico que las convertiría en propuestas de reglas queda para cuando haya volumen
    suficiente de proyectos (ver plan de evolución del documento de arquitectura).
    """

    __tablename__ = "ai_feedback_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    # Nullable porque un evento de tipo "engineering" no tiene budget asociado, y porque
    # filas creadas antes de esta columna (ninguna en el ambiente real hoy) quedarían sin
    # valor. Necesario para el análisis de Motor 7: un proyecto puede tener más de un
    # Budget, así que project_id solo no basta para saber qué otros productos había en el
    # presupuesto cuando ocurrió este evento (§ docs/ai-engine-architecture.md).
    budget_id: Mapped[int | None] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(20))
    origin: Mapped[str] = mapped_column(String(20))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    field_changed: Mapped[str | None] = mapped_column(String(40), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
