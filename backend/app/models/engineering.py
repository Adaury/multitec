from sqlalchemy import ForeignKey, Text
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

    project: Mapped["Project"] = relationship(back_populates="engineering")
