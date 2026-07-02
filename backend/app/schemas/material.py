from datetime import datetime

from pydantic import BaseModel


class MaterialCreate(BaseModel):
    product_id: int | None = None
    description: str
    quantity: float = 1
    notes: str | None = None


class MaterialStatusUpdate(BaseModel):
    status: str


class MaterialOut(BaseModel):
    id: int
    project_id: int
    product_id: int | None
    source_quote_id: int | None
    description: str
    quantity: float
    status: str
    notes: str | None
    created_at: datetime

    class Config:
        from_attributes = True
