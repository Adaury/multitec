from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

MATERIAL_STATUSES = ("disponible", "pendiente_compra", "comprado", "instalado")


class Material(Base):
    """Inventario simple (§18) — un material del proyecto con estado."""

    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    source_quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    status: Mapped[str] = mapped_column(String(20), default="pendiente_compra")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    # A quién se le compró y a qué precio real (distinto de Product.price/cost, que son
    # estimados de catálogo) — se completan cuando el material se marca "comprado", pero
    # quedan opcionales (se pueden cargar después) igual que `reason` en StockMovement.
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.id"), nullable=True)
    purchase_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="materials")
    supplier: Mapped["Supplier | None"] = relationship(back_populates="materials")

    @property
    def supplier_name(self) -> str | None:
        return self.supplier.name if self.supplier else None

    @property
    def project_code(self) -> str:
        return self.project.code
