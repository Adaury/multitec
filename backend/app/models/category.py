from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Category(Base):
    """Nodo de clasificación de catálogo (§ catálogo inteligente v2). Auto-referencial:
    `parent_id` nulo = categoría raíz (ej. "CCTV"); con `parent_id` = subcategoría (ej.
    "Cámaras IP"). `code_prefix` es opcional — un producto resuelve el suyo caminando hacia
    los ancestros hasta encontrar el primero que lo tenga (ver Product.resolve_code_prefix),
    así que solo hace falta declararlo donde cambia."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    code_prefix: Mapped[str | None] = mapped_column(String(10), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    parent: Mapped["Category | None"] = relationship(remote_side=[id], back_populates="children")
    children: Mapped[list["Category"]] = relationship(back_populates="parent")
