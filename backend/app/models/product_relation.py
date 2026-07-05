from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

RELATION_TYPE_COMPATIBLE = "compatible_con"
RELATION_TYPE_ALTERNATIVE = "alternativa_de"
RELATION_TYPE_REQUIRES = "requiere"
RELATION_TYPES = (RELATION_TYPE_COMPATIBLE, RELATION_TYPE_ALTERNATIVE, RELATION_TYPE_REQUIRES)


class ProductRelation(Base):
    """Relación informativa entre dos productos del catálogo (§ docs/ai-engine-architecture.md,
    Motor 2) — deliberadamente separada de `CatalogRule`/`TechnicalRule`: esto es
    información para quien arma el presupuesto a mano (ej. "este switch requiere este
    tipo de fuente"), no una acción que se dispare automáticamente. Se guarda una sola
    fila dirigida (`product_id` → `related_product_id`); consultar las relaciones de un
    producto revisa ambos lados (ver `list_product_relations` en api/routers/catalog.py),
    así que no hace falta duplicar la fila inversa para los tipos simétricos
    (`compatible_con`, `alternativa_de`).
    """

    __tablename__ = "product_relations"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    related_product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"), index=True)
    relation_type: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    product: Mapped["Product"] = relationship(foreign_keys=[product_id])  # noqa: F821
    related_product: Mapped["Product"] = relationship(foreign_keys=[related_product_id])  # noqa: F821
