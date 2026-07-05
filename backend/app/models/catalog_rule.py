from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class CatalogRule(Base):
    """Regla de sugerencia de accesorios con cantidad (§ catálogo inteligente v2).

    Colgada de un producto "fuente" (ej. una cámara IP); `target_tag` identifica el
    accesorio a proponer buscando un producto del catálogo cuyo `tags` lo contenga.
    `per_source_units` nulo = modo fijo (agrega `quantity` una sola vez, ej. "1 NVR" sin
    importar cuántas cámaras haya). Con valor = modo proporcional: por cada
    `per_source_units` unidades del producto fuente se agregan `quantity` unidades del
    accesorio, redondeando lotes hacia arriba (ver ai_engine/rules.py).
    """

    __tablename__ = "catalog_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    target_tag: Mapped[str] = mapped_column(String(60))
    per_source_units: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    source_product: Mapped["Product"] = relationship(back_populates="rules")  # noqa: F821
