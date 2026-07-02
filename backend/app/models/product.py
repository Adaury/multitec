from sqlalchemy import Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# Prefijo de código por categoría de catálogo
CATEGORY_PREFIXES = {
    "camara": "CAM",
    "nvr": "NVR",
    "cableado": "CAB",
    "switch": "SW",
    "control_acceso": "ACC",
    "videoportero": "VP",
    "barrera": "BAR",
    "automatizacion": "AUT",
    "otro": "OTR",
}


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    category: Mapped[str] = mapped_column(String(30))
    name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(20), default="unidad")
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
