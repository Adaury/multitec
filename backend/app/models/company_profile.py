from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompanyProfile(Base):
    """Datos de la empresa que salen en el membrete de cotizaciones y facturas (una sola fila).
    Cada campo vacío (NULL) cae al valor de COMPANY_* en `.env`: así una instalación que ya
    tenía el membrete en `.env` sigue igual hasta que alguien lo edite desde la app."""

    __tablename__ = "company_profile"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    tagline: Mapped[str | None] = mapped_column(String(160), nullable=True)
    representative: Mapped[str | None] = mapped_column(String(120), nullable=True)
    rnc: Mapped[str | None] = mapped_column(String(30), nullable=True)
    cedula: Mapped[str | None] = mapped_column(String(30), nullable=True)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(60), nullable=True)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    website: Mapped[str | None] = mapped_column(String(120), nullable=True)
    bank_info: Mapped[str | None] = mapped_column(Text, nullable=True)
    invoice_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    logo_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
