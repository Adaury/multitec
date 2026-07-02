from datetime import datetime

from pydantic import BaseModel


class QuoteItemIn(BaseModel):
    product_id: int | None = None
    description: str
    quantity: float = 1
    unit_price: float = 0


class QuoteCreate(BaseModel):
    notes: str | None = None
    items: list[QuoteItemIn] = []


class QuoteUpdate(QuoteCreate):
    pass


class QuoteItemOut(BaseModel):
    id: int
    product_id: int | None
    description: str
    quantity: float
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class QuoteOut(BaseModel):
    id: int
    code: str
    project_id: int
    source_budget_id: int | None
    status: str
    notes: str | None
    subtotal: float
    itbis: float
    total: float
    created_at: datetime
    decided_at: datetime | None
    items: list[QuoteItemOut] = []

    class Config:
        from_attributes = True


class QuoteHistoryOut(BaseModel):
    id: int
    action: str
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class RejectIn(BaseModel):
    reason: str
