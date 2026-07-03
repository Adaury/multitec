from datetime import datetime

from pydantic import BaseModel, Field


class ProductCreate(BaseModel):
    category: str = Field(max_length=100)
    name: str = Field(max_length=255)
    unit: str = Field(default="unidad", max_length=30)
    price: float = 0
    notes: str | None = Field(default=None, max_length=2000)


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=30)
    price: float | None = None
    notes: str | None = Field(default=None, max_length=2000)


class ProductOut(BaseModel):
    id: int
    code: str
    category: str
    name: str
    unit: str
    price: float
    stock_quantity: float
    notes: str | None
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
