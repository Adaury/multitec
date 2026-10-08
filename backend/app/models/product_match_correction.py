from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProductMatchCorrection(Base):
    """Aprendizaje de sinónimos (Motor 7): lo que el técnico dijo ("domo", "cable de red") y el
    producto que un humano puso en su lugar al corregir un presupuesto generado por la IA.
    `ai_product_id` es lo que había puesto la IA (None = no logró emparejarlo). Con la misma
    frase corregida al mismo producto varias veces, el emparejamiento deja de depender del
    modelo (ver `app.ai_engine.learning.get_learned_matches`) y se le propone al admin
    agregar la frase como sinónimo del producto."""

    __tablename__ = "product_match_corrections"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    budget_id: Mapped[int | None] = mapped_column(ForeignKey("budgets.id", ondelete="CASCADE"), nullable=True)
    spoken_text: Mapped[str] = mapped_column(String(255))
    ai_product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    human_product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
