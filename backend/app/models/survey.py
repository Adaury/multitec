from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Survey(Base):
    """Levantamiento técnico — 1:1 con Project."""

    __tablename__ = "surveys"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), unique=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurements: Mapped[str | None] = mapped_column(Text, nullable=True)
    observations: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)  # gancho para IA (Fase 5)

    project: Mapped["Project"] = relationship(back_populates="survey")
    assets: Mapped[list["SurveyAsset"]] = relationship(back_populates="survey", cascade="all, delete-orphan")


class SurveyAsset(Base):
    """Foto o audio adjunto a un levantamiento."""

    __tablename__ = "survey_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    survey_id: Mapped[int] = mapped_column(ForeignKey("surveys.id"))
    kind: Mapped[str] = mapped_column(String(10))  # photo | audio
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    survey: Mapped["Survey"] = relationship(back_populates="assets")
