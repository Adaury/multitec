from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.timeutil import today_dr
from app.db.base import Base

PROJECT_STATES = (
    "levantamiento",
    "ingenieria",
    "presupuesto",
    "cotizacion",
    "ejecucion",
    "cerrado",
)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    responsible_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    date: Mapped[date] = mapped_column(Date, default=today_dr)
    status: Mapped[str] = mapped_column(String(30), default="levantamiento")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Ubicación del sitio de ESTE proyecto (un cliente puede tener varias obras). Si está
    # vacía, se usa la del cliente — ver `Project.place_address/place_location_url`.
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    location_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    # Token opaco para el portal de cliente (sin login) — NULL = portal desactivado. Ver
    # api/routers/public.py. No usar el id numérico como identificador público: sería
    # trivial enumerar todos los proyectos de la empresa.
    public_token: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    # Tracking del portal de cliente — se actualizan en cada GET público (ver
    # api/routers/public.py). `portal_first_viewed_at` dispara una notificación única a
    # los admins (§ notify_portal_first_viewed); `portal_last_viewed_at` solo se muestra
    # en la ficha del proyecto, sin generar ruido en cada refresco.
    portal_first_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    portal_last_viewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    client: Mapped["Client"] = relationship(back_populates="projects")
    responsible: Mapped["User"] = relationship(foreign_keys=[responsible_id])
    survey: Mapped["Survey"] = relationship(back_populates="project", uselist=False, cascade="all, delete-orphan")
    engineering: Mapped["Engineering"] = relationship(
        back_populates="project", uselist=False, cascade="all, delete-orphan"
    )
    budgets: Mapped[list["Budget"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    materials: Mapped[list["Material"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    stages: Mapped[list["ProjectStage"]] = relationship(
        back_populates="project", cascade="all, delete-orphan", order_by="ProjectStage.order"
    )
    log_entries: Mapped[list["LogEntry"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    pre_invoices: Mapped[list["PreInvoice"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    extensions: Mapped[list["Extension"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    @property
    def place_address(self) -> str | None:
        """Dirección del sitio: la del proyecto, o la del cliente si el proyecto no tiene."""
        return self.address or self.client.address

    @property
    def place_location_url(self) -> str | None:
        """Enlace de ubicación del sitio: el del proyecto, o el del cliente como respaldo."""
        return self.location_url or self.client.location_url
