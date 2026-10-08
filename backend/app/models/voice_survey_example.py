from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class VoiceSurveyExample(Base):
    """Aprendizaje del levantamiento por voz (Motor 7): lo que dijo el técnico, cómo lo
    repartió la IA entre Notas/Medidas/Observaciones y cómo lo dejó el técnico tras revisarlo.
    `corrected` marca las filas donde el técnico cambió algo — esas son las que más enseñan,
    y las más recientes se le muestran al modelo como ejemplos en el siguiente dictado (ver
    `app.ai_engine.learning.recent_voice_examples`)."""

    __tablename__ = "voice_survey_examples"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    transcript: Mapped[str] = mapped_column(Text)
    ai_notes: Mapped[str] = mapped_column(Text, default="")
    ai_measurements: Mapped[str] = mapped_column(Text, default="")
    ai_observations: Mapped[str] = mapped_column(Text, default="")
    final_notes: Mapped[str] = mapped_column(Text, default="")
    final_measurements: Mapped[str] = mapped_column(Text, default="")
    final_observations: Mapped[str] = mapped_column(Text, default="")
    # False cuando la IA no pudo repartir (todo quedó en Notas): ahí lo que el técnico mueve a
    # mano es el reparto "correcto" completo, no una corrección fina.
    ai_classified: Mapped[bool] = mapped_column(Boolean, default=True)
    corrected: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
