from datetime import datetime

from pydantic import BaseModel, Field


class MaterialCreate(BaseModel):
    product_id: int | None = None
    description: str = Field(max_length=500)
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=2000)


class MaterialStatusUpdate(BaseModel):
    status: str = Field(max_length=30)


class MaterialOut(BaseModel):
    id: int
    project_id: int
    product_id: int | None
    source_quote_id: int | None
    description: str
    quantity: float
    status: str
    notes: str | None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
