from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

STOCK_MOVEMENT_TYPES = ("entrada", "salida")


class StockMovement(Base):
    """Control de inventario de bodega — entradas/salidas de stock por producto del
    catálogo, independiente de los materiales asignados a un proyecto (Material, §18)."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    movement_type: Mapped[str] = mapped_column(String(10))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2))
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(back_populates="stock_movements")
