from datetime import date, datetime, time

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text, Time, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.tenant import TenantMixin

# "en_sitio" = el técnico ya llegó (marcó entrada) y todavía no terminó.
VISIT_STATUSES = ("programada", "en_sitio", "completada", "cancelada")


class Visit(TenantMixin, Base):
    """Visita técnica agendada a un proyecto — calendario simple por fecha."""

    __tablename__ = "visits"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    technician_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True, nullable=True)
    # El calendario filtra por rango de fechas; el índice ya existe en la base (ix_visits_scheduled_date),
    # aquí se declara para que el modelo y la migración no diverjan.
    scheduled_date: Mapped[date] = mapped_column(Date, index=True)
    scheduled_time: Mapped[time | None] = mapped_column(Time, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="programada")
    # Duración estimada, para avisar de choques de horario del técnico.
    duration_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Entrada y salida del técnico en el sitio. Las coordenadas solo se capturan al tocar el botón (no hay
    # seguimiento continuo) y son opcionales: sin GPS o sin permiso la hora igual queda registrada.
    checkin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkin_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkin_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    checkout_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    checkout_lng: Mapped[float | None] = mapped_column(Float, nullable=True)
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
    def minutes_on_site(self) -> int | None:
        """Minutos entre la entrada y la salida marcadas (None mientras falte alguna)."""
        if self.checkin_at is None or self.checkout_at is None:
            return None
        return max(0, round((self.checkout_at - self.checkin_at).total_seconds() / 60))

    @property
    def client_address(self) -> str | None:
        return self.project.place_address

    @property
    def client_location_url(self) -> str | None:
        return self.project.place_location_url

    @property
    def client_phone(self) -> str | None:
        return self.project.client.phone

    @property
    def technician_name(self) -> str | None:
        return self.technician.name if self.technician else None
