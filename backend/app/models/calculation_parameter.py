from datetime import datetime

from sqlalchemy import DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CalculationParameter(Base):
    """Parámetro configurable de Motor 5 (§ docs/ai-engine-architecture.md) —
    clave/valor administrable desde el ERP en vez de una constante en código. Sin fila
    para una clave conocida = se usa el default de código (ver
    `app.ai_engine.calculation.KNOWN_PARAMETERS`), así que esta tabla nunca necesita
    poblarse por adelantado para que el cálculo funcione."""

    __tablename__ = "calculation_parameters"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(60), unique=True, index=True)
    value: Mapped[float] = mapped_column(Numeric(12, 4))
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)
