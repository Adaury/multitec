from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
