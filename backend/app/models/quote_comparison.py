from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.tenant import TenantMixin


class QuoteComparison(TenantMixin, Base):
    """Una cotización ajena (de un competidor o de un proveedor) que se subió para compararla con el levantamiento y con
    la cotización propia. Guarda el archivo, el texto que se leyó y las líneas que la IA entendió (`items`, que oficina
    puede corregir). El resultado de la comparación NO se guarda: se calcula cada vez con la cotización y el levantamiento
    de ese momento (ver services/quote_compare.py)."""

    __tablename__ = "quote_comparisons"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    # Cotización propia contra la que se compara; vacía = la más reciente del proyecto.
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    label: Mapped[str] = mapped_column(String(120))
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    # [{"description": str, "quantity": float, "unit_price": float}]
    items: Mapped[list] = mapped_column(JSON, default=list)
    # Total que dice el documento (con o sin ITBIS, según venga); vacío si no lo trae.
    total: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
