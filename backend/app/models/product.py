from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Prefijo de respaldo cuando ninguna categoría/ancestro en la cadena declaró code_prefix
# (§ catálogo inteligente v2 — ver app/db/taxonomy.py, categoría "Otros").
FALLBACK_CODE_PREFIX = "OTR"


def resolve_code_prefix(category: "Category | None") -> str:
    """Prefijo de código para un producto: camina la cadena de ancestros de `category`
    hasta encontrar el primero con `code_prefix` propio (ej. "Cámaras IP" hereda "CAM" de
    sí misma; "Accesorios" bajo CCTV cae al fallback porque ni ella ni CCTV lo declaran)."""
    node = category
    while node is not None:
        if node.code_prefix:
            return node.code_prefix
        node = node.parent
    return FALLBACK_CODE_PREFIX


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(150))
    unit: Mapped[str] = mapped_column(String(20), default="unidad")
    price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    stock_quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    brand: Mapped[str | None] = mapped_column(String(80), nullable=True)
    model: Mapped[str | None] = mapped_column(String(80), nullable=True)
    commercial_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    technical_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Catálogo "inteligente" (§ levantamiento con IA): tags/synonyms alimentan el matching
    # semántico en suggest_budget_items. Las reglas de accesorios con cantidad viven en
    # CatalogRule (source_product_id → este producto), no aquí. JSON (no ARRAY) para
    # funcionar igual en SQLite y Postgres, mismo patrón que ProjectEmbedding.embedding.
    tags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    synonyms: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    category: Mapped["Category | None"] = relationship()
    stock_movements: Mapped[list["StockMovement"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        order_by="StockMovement.created_at.desc(), StockMovement.id.desc()",
    )
    rules: Mapped[list["CatalogRule"]] = relationship(back_populates="source_product", cascade="all, delete-orphan")

    @property
    def category_name(self) -> str | None:
        return self.category.name if self.category else None

    @property
    def category_path(self) -> str | None:
        """Ruta legible de la clasificación, ej. 'CCTV › Cámaras IP', para mostrar en el
        catálogo sin que el frontend tenga que caminar el árbol de categorías."""
        if self.category is None:
            return None
        parts: list[str] = []
        node = self.category
        while node is not None:
            parts.append(node.name)
            node = node.parent
        return " › ".join(reversed(parts))
