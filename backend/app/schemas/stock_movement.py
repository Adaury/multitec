from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class StockMovementCreate(BaseModel):
    movement_type: Literal["entrada", "salida"]
    quantity: float = Field(gt=0)
    reason: str | None = Field(default=None, max_length=2000)


class StockMovementOut(BaseModel):
    id: int
    product_id: int
    movement_type: str
    quantity: float
    reason: str | None
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True
