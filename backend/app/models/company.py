from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, false, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COMPANY_SUSPENDED = "Tu empresa está suspendida. Contacta al administrador de la plataforma."
COMPANY_TRIAL_ENDED = "El periodo de prueba de tu empresa terminó. Contacta al administrador de la plataforma."


class Company(Base):
    """Una empresa que usa el sistema. Todo lo demás (clientes, proyectos, facturas, usuarios...) cuelga de una
    empresa por `company_id` y nadie ve datos de otra (ver app/db/tenant.py). La empresa 1 es la original
    (Multitec): la migración le asigna todo lo que ya existía.

    No lleva `company_id` ella misma ni es "de empresa": la ve el panel de plataforma."""

    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    # Suspendida = nadie de la empresa puede entrar (ni por el portal de sus clientes) hasta reactivarla.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Periodo de prueba: pasada esta fecha la empresa deja de entrar igual que si estuviera suspendida; el panel de
    # plataforma la extiende. Vacío = sin vencimiento (la empresa original y las que ya pagan).
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Tope de usuarios activos que puede tener la empresa. Vacío = sin tope.
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Empresa creada para que los técnicos prueben la app (con datos de ejemplo y usuarios de prueba).
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def trial_expired(self) -> bool:
        if self.trial_ends_at is None:
            return False
        ends = self.trial_ends_at if self.trial_ends_at.tzinfo else self.trial_ends_at.replace(tzinfo=timezone.utc)
        return ends <= datetime.now(timezone.utc)

    @property
    def access_block_reason(self) -> str | None:
        """Por qué nadie de esta empresa puede entrar ahora (None = puede)."""
        if not self.is_active:
            return COMPANY_SUSPENDED
        if self.trial_expired:
            return COMPANY_TRIAL_ENDED
        return None
