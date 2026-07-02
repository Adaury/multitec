from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

STAGE_NAMES = ("inicio", "instalacion", "configuracion", "pruebas", "entrega")


class ProjectStage(Base):
    """Ejecución por etapas (§11) — orden fijo y secuencial."""

    __tablename__ = "project_stages"
    __table_args__ = (UniqueConstraint("project_id", "name", name="uq_project_stage"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    name: Mapped[str] = mapped_column(String(20))
    order: Mapped[int] = mapped_column(Integer)
    completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="stages")
