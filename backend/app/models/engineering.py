from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Engineering(Base):
    """Ingeniería — 1:1 con Project."""

    __tablename__ = "engineering"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    recommended_equipment: Mapped[str | None] = mapped_column(Text, nullable=True)
    distribution: Mapped[str | None] = mapped_column(Text, nullable=True)
    conduits: Mapped[str | None] = mapped_column(Text, nullable=True)
    wiring: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_design: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    # True mientras el contenido sea exactamente el borrador que puso la IA (§ Motor 7,
    # docs/ai-engine-architecture.md) — se pone en False en la primera edición humana,
    # momento en el que se registra qué campo cambió como AIFeedbackEvent (ver
    # app.ai_engine.learning). Rellenada a mano nunca lo activa.
    ai_generated: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="engineering")
