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
    # "panel" = lo escribió el dueño; "cliente" = lo envió un cliente desde la página pública (llega sin publicar).
    source: Mapped[str] = mapped_column(String(20), default="panel", server_default="panel")
    # Teléfono o correo de quien lo envió, para confirmar antes de publicar. Nunca se muestra en la página.
    contact: Mapped[str | None] = mapped_column(String(160), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class SitePartner(Base):
    """Empresa aliada que se muestra en la página pública (p. ej. una que tiene a Multitec como socio). `logo_url` es una
    ruta de la propia web (/brand/...) o vacía: no se enlazan logos de otros sitios."""

    __tablename__ = "site_partners"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(300), nullable=True)
    published: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    sort: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
