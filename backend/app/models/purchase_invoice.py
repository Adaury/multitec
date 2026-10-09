from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# Tipo de Bienes y Servicios Comprados (columna 3 del 606): códigos 01-11 de la DGII.
EXPENSE_TYPES = tuple(f"{i:02d}" for i in range(1, 12))
# Forma de pago (última columna del 606): 01 efectivo, 02 cheque/transferencia/depósito,
# 03 tarjeta, 04 compra a crédito, 05 permuta, 06 notas de crédito, 07 mixto.
PAYMENT_TYPES = tuple(f"{i:02d}" for i in range(1, 8))


class PurchaseInvoice(Base):
    """Factura de proveedor (compra) — insumo del reporte 606 (Compras) de la DGII.
    Es independiente de Material: aquí se registra el comprobante fiscal (NCF, ITBIS,
    retenciones), no el material asignado a un proyecto."""

    __tablename__ = "purchase_invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    project_id: Mapped[int | None] = mapped_column(ForeignKey("projects.id"), nullable=True, index=True)
    ncf: Mapped[str] = mapped_column(String(19))
    ncf_modified: Mapped[str | None] = mapped_column(String(19), nullable=True)
    invoice_date: Mapped[date] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expense_type: Mapped[str] = mapped_column(String(2), default="09")
    payment_type: Mapped[str] = mapped_column(String(2), default="04")
    services_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    goods_amount: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    itbis_invoiced: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    itbis_withheld: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    isr_withheld: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    supplier: Mapped["Supplier"] = relationship()
