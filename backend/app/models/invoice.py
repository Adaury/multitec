from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PreInvoice(Base):
    """Prefactura (§13) — documento previo, subtotal/ITBIS/total."""

    __tablename__ = "pre_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    source_quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pendiente")  # pendiente | facturada
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    itbis: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    project: Mapped["Project"] = relationship(back_populates="pre_invoices")
    items: Mapped[list["PreInvoiceItem"]] = relationship(back_populates="pre_invoice", cascade="all, delete-orphan")
    invoice: Mapped["Invoice"] = relationship(back_populates="pre_invoice", uselist=False)


class PreInvoiceItem(Base):
    __tablename__ = "pre_invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    pre_invoice_id: Mapped[int] = mapped_column(ForeignKey("pre_invoices.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    pre_invoice: Mapped["PreInvoice"] = relationship(back_populates="items")


class Invoice(Base):
    """Factura (§14) — conversión manual desde Prefactura, solo admin."""

    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    pre_invoice_id: Mapped[int] = mapped_column(ForeignKey("pre_invoices.id"), unique=True)
    ncf: Mapped[str | None] = mapped_column(String(20), unique=True, nullable=True)
    ncf_type: Mapped[str | None] = mapped_column(String(3), nullable=True)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    itbis: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    total: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="invoices")
    pre_invoice: Mapped["PreInvoice"] = relationship(back_populates="invoice")
    items: Mapped[list["InvoiceItem"]] = relationship(back_populates="invoice", cascade="all, delete-orphan")
    history: Mapped[list["InvoiceHistory"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceHistory.created_at"
    )


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"), nullable=True)
    description: Mapped[str] = mapped_column(String(255))
    quantity: Mapped[float] = mapped_column(Numeric(12, 2), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    subtotal: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="items")


class InvoiceHistory(Base):
    __tablename__ = "invoice_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"))
    action: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    invoice: Mapped["Invoice"] = relationship(back_populates="history")
