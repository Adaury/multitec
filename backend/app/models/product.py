from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
    stock_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="StockMovement.created_at.desc(), StockMovement.id.desc()",
    )
