from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

VISIT_STATUSES = ("programada", "completada", "cancelada")


class Visit(Base):
    """Visita técnica agendada a un proyecto — calendario simple por fecha."""

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    scheduled_date: Mapped[date] = mapped_column(Date)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="programada")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project: Mapped["Project"] = relationship()
    technician: Mapped["User"] = relationship(foreign_keys=[technician_id])

    @property
    def project_code(self) -> str:
        return self.project.code

    @property
    def client_name(self) -> str:
        return self.project.client.name

    @property
    def technician_name(self) -> str | None:
        return self.technician.name if self.technician else None
