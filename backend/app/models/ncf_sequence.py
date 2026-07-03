from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class NcfSequence(Base):
    """Rango de Números de Comprobante Fiscal (NCF) autorizado por la DGII para un tipo
    de comprobante (B01 crédito fiscal, B02 consumo, B14 regímenes especiales, B15
    gubernamental...). `next_number` avanza en cada factura emitida con este tipo."""

    __tablename__ = "ncf_sequences"

    id: Mapped[int] = mapped_column(primary_key=True)
    ncf_type: Mapped[str] = mapped_column(String(3))
    description: Mapped[str] = mapped_column(String(100))
    range_start: Mapped[int] = mapped_column(Integer)
    range_end: Mapped[int] = mapped_column(Integer)
    next_number: Mapped[int] = mapped_column(Integer)
    expires_at: Mapped[date] = mapped_column(Date)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
