from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.tenant import TenantMixin

TICKET_STATUSES = ("abierto", "en_proceso", "resuelto", "cerrado")


class Ticket(TenantMixin, Base):
    """Ticket de soporte (§16) — siempre pertenece a un proyecto."""

    __tablename__ = "tickets"
    # Único por empresa, no global: cada empresa lleva sus propios correlativos.
    __table_args__ = (UniqueConstraint("company_id", "code", name="uq_tickets_company_code"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    problem: Mapped[str] = mapped_column(Text)
    solution: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="abierto")
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="tickets")
    technician: Mapped["User"] = relationship(foreign_keys=[technician_id])
    history: Mapped[list["TicketHistory"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", order_by="TicketHistory.created_at"
    )
    assets: Mapped[list["TicketAsset"]] = relationship(back_populates="ticket", cascade="all, delete-orphan")


class TicketHistory(TenantMixin, Base):
    __tablename__ = "ticket_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    action: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["Ticket"] = relationship(back_populates="history")


class TicketAsset(TenantMixin, Base):
    """Foto de evidencia adjunta a un ticket (p. ej. al resolverlo)."""

    __tablename__ = "ticket_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[int] = mapped_column(ForeignKey("tickets.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    ticket: Mapped["Ticket"] = relationship(back_populates="assets")
