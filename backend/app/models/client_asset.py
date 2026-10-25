from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Tipos de equipo que se ofrecen en la app; en la base es texto libre para no obligar a migrar por cada tipo nuevo.
ASSET_KINDS = (
    "camara",
    "grabador",
    "panel_alarma",
    "sensor",
    "control_acceso",
    "cerradura",
    "intercomunicador",
    "switch",
    "router_wifi",
    "ups",
    "otro",
)


class ClientAsset(Base):
    """Un equipo instalado en casa o local de un cliente: qué es, dónde está, su serial y MAC, cuándo se instaló
    y hasta cuándo tiene garantía. Es la base para garantías y mantenimientos: al llegar una falla se sabe qué
    equipo es y si todavía está cubierto."""

    __tablename__ = "client_assets"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), index=True)
    # El proyecto con el que se instaló (opcional: puede ser un equipo anterior al sistema).
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), index=True, nullable=True)
    kind: Mapped[str] = mapped_column(String(40), default="otro")
    name: Mapped[str] = mapped_column(String(120))
    brand: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model: Mapped[str | None] = mapped_column(String(60), nullable=True)
    serial: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    mac: Mapped[str | None] = mapped_column(String(17), index=True, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    location: Mapped[str | None] = mapped_column(String(160), nullable=True)  # "entrada principal", "sala"
    installed_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    warranty_until: Mapped[date | None] = mapped_column(Date, index=True, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
