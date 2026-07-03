from datetime import datetime

from pydantic import BaseModel, Field


class BudgetItemIn(BaseModel):
    product_id: int | None = None
    description: str = Field(max_length=500)
    quantity: float = 1
    unit_price: float = 0  # usado solo para calcular el total; no se expone en la salida


class BudgetCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
    items: list[BudgetItemIn] = []


class BudgetUpdate(BudgetCreate):
    pass


class BudgetItemOut(BaseModel):
    """Salida pública de línea de presupuesto: SIN precio unitario (regla de negocio)."""

    id: int
    description: str
    quantity: float
    product_id: int | None

    class Config:
        from_attributes = True


class BudgetOut(BaseModel):
    id: int
    code: str
    project_id: int
    notes: str | None
    total: float
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[BudgetItemOut] = []

    class Config:
        from_attributes = True
