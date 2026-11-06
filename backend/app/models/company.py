from datetime import date, datetime, timedelta, timezone

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, false, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

COMPANY_SUSPENDED = "Tu empresa está suspendida. Contacta al administrador de la plataforma."
COMPANY_TRIAL_ENDED = "El periodo de prueba de tu empresa terminó. Contacta al administrador de la plataforma."
COMPANY_PAYMENT_OVERDUE = (
    "La mensualidad de tu empresa está vencida. Realiza el pago y avísale a Multitec para reactivar el acceso."
)
# Días después de «pagado hasta» en que la empresa sigue entrando (con aviso) antes de quedar bloqueada.
GRACE_DAYS = 5


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


class Company(Base):
    """Una empresa que usa el sistema. Todo lo demás (clientes, proyectos, facturas, usuarios...) cuelga de una
    empresa por `company_id` y nadie ve datos de otra (ver app/db/tenant.py). La empresa 1 es la original
    (Multitec): la migración le asigna todo lo que ya existía.

    No lleva `company_id` ella misma ni es "de empresa": la ve el panel de plataforma.

    Suscripción: una empresa nueva empieza en prueba (`trial_ends_at`). Cuando paga, se registra el pago en el panel y
    pasa a tener `paid_until` (la prueba se quita). Pasado `paid_until` + GRACE_DAYS deja de entrar. Sin prueba ni
    `paid_until` (la empresa original) no vence nunca."""

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

    # De dónde salió: "panel" (la creó la plataforma) o "registro" (se registró sola desde la página pública).
    source: Mapped[str] = mapped_column(String(20), default="panel", server_default="panel")
    contact_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Lo que se le cobra a esta empresa (RD$). Vacío = la tarifa general de la configuración.
    setup_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    setup_paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # Cuándo la plataforma vio la solicitud de una empresa registrada sola (vacío = solicitud nueva).
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    @property
    def trial_expired(self) -> bool:
        if self.trial_ends_at is None:
            return False
        return _utc(self.trial_ends_at) <= datetime.now(timezone.utc)

    @property
    def payment_overdue(self) -> bool:
        """Pasó «pagado hasta» (todavía puede estar dentro de los días de gracia)."""
        return self.paid_until is not None and _utc(self.paid_until) <= datetime.now(timezone.utc)

    @property
    def payment_cut_off(self) -> bool:
        """Pasaron también los días de gracia: ya no entra."""
        return self.paid_until is not None and _utc(self.paid_until) + timedelta(days=GRACE_DAYS) <= datetime.now(timezone.utc)

    @property
    def access_block_reason(self) -> str | None:
        """Por qué nadie de esta empresa puede entrar ahora (None = puede)."""
        if not self.is_active:
            return COMPANY_SUSPENDED
        if self.paid_until is not None:
            return COMPANY_PAYMENT_OVERDUE if self.payment_cut_off else None
        if self.trial_expired:
            return COMPANY_TRIAL_ENDED
        return None

    @property
    def state(self) -> str:
        """suspendida | prueba | vencida (prueba terminada) | atrasada (en días de gracia) | cortada | activa"""
        if not self.is_active:
            return "suspendida"
        if self.paid_until is not None:
            if self.payment_cut_off:
                return "cortada"
            return "atrasada" if self.payment_overdue else "activa"
        if self.trial_ends_at is not None:
            return "vencida" if self.trial_expired else "prueba"
        return "activa"

    @property
    def ends_at(self) -> datetime | None:
        """La próxima fecha que importa: fin de la prueba o «pagado hasta»."""
        return self.paid_until if self.paid_until is not None else self.trial_ends_at

    @property
    def days_left(self) -> int | None:
        ends = self.ends_at
        if ends is None:
            return None
        return (_utc(ends) - datetime.now(timezone.utc)).days


class CompanyPayment(Base):
    """Un pago de una empresa a la plataforma (instalación y explicación, o mensualidad). Lo registra la plataforma a
    mano (transferencia, efectivo...). No es «de empresa» (sin TenantMixin): solo lo ven el panel de plataforma y, de
    lo suyo, el administrador de esa empresa en «Mi suscripción»."""

    __tablename__ = "company_payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))  # instalacion | mensualidad
    amount: Mapped[float] = mapped_column(Numeric(12, 2))
    months: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    method: Mapped[str] = mapped_column(String(20))  # transferencia | efectivo | tarjeta | deposito | otro
    reference: Mapped[str | None] = mapped_column(String(120), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[date] = mapped_column(Date)
    # Cómo quedó «pagado hasta» después de este pago (para el historial).
    paid_until_after: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    recorded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
