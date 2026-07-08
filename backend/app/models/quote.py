from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

QUOTE_STATUSES = ("pendiente", "aprobada", "no_aprobada", "archivada")


class Quote(Base):
    """Cotización — documento detallado con ITBIS y estados."""

    __tablename__ = "quotes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    source_budget_id: Mapped[int | None] = mapped_column(ForeignKey("budgets.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pendiente")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    itbis: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="quotes")
    items: Mapped[list["QuoteItem"]] = relationship(back_populates="quote", cascade="all, delete-orphan")
    history: Mapped[list["QuoteHistory"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", order_by="QuoteHistory.created_at"
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    # Nota corta por línea (§ editor de ítems) — a diferencia del resto de la fila, esta sí
    # se guarda: el usuario la escribe para que salga impresa en el PDF, no como scratchpad.
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    quote: Mapped["Quote"] = relationship(back_populates="items")


class QuoteHistory(Base):
    __tablename__ = "quote_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    quote_id: Mapped[int] = mapped_column(ForeignKey("quotes.id"))
    action: Mapped[str] = mapped_column(String(20))  # creada|aprobada|rechazada|archivada|reactivada|editada
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    quote: Mapped["Quote"] = relationship(back_populates="history")
