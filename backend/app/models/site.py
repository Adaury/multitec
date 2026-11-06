from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, Numeric, String, Text, false, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PlatformPlan(Base):
    """Plan que se vende en la página pública y en el registro (como los de ZuraPOS: Básico, Profesional,
    Empresarial). Precios en la moneda de la plataforma (PLATFORM_CURRENCY). Lo edita el dueño desde el panel.
    No es «de empresa»: lo ve todo el mundo."""

    __tablename__ = "platform_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    monthly_price: Mapped[float] = mapped_column(Numeric(12, 2))
    setup_price: Mapped[float] = mapped_column(Numeric(12, 2))
    max_users: Mapped[int | None] = mapped_column(Integer, nullable=True)  # vacío = sin tope
    features: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    highlighted: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Testimonial(Base):
    """Opinión de un cliente para la página pública. Solo se muestran las publicadas; `is_example` marca los
    borradores de muestra que trae el sistema (no deben publicarse sin reemplazarlos por una opinión real)."""

    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(primary_key=True)
    author: Mapped[str] = mapped_column(String(120))
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    company: Mapped[str | None] = mapped_column(String(120), nullable=True)
    quote: Mapped[str] = mapped_column(Text)
    rating: Mapped[int] = mapped_column(Integer, default=5, server_default="5")
    published: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    is_example: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
