from datetime import datetime

from pydantic import BaseModel, Field


class PreInvoiceItemIn(BaseModel):
    product_id: int | None = None
    description: str = Field(max_length=500)
    quantity: float = 1
    unit_price: float = 0


class PreInvoiceCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
    items: list[PreInvoiceItemIn] = []


class PreInvoiceItemOut(BaseModel):
    id: int
    product_id: int | None
    description: str
    quantity: float
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class PreInvoiceOut(BaseModel):
    id: int
    code: str
    project_id: int
    source_quote_id: int | None
    status: str
    notes: str | None
    subtotal: float
    itbis: float
    total: float
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
    items: list[PreInvoiceItemOut] = []

    class Config:
        from_attributes = True


class InvoiceItemOut(BaseModel):
    id: int
    product_id: int | None
    description: str
    quantity: float
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class InvoiceOut(BaseModel):
    id: int
    code: str
    project_id: int
    pre_invoice_id: int
    ncf: str | None = None
    ncf_type: str | None = None
    subtotal: float
    itbis: float
    total: float
    created_by: int | None = None
    created_at: datetime
    items: list[InvoiceItemOut] = []

    class Config:
        from_attributes = True


class InvoiceHistoryOut(BaseModel):
    id: int
    action: str
    note: str | None
    created_at: datetime

    class Config:
        from_attributes = True
