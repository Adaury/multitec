from datetime import date, datetime

from pydantic import BaseModel


class PublicQuoteItemOut(BaseModel):
    description: str
    quantity: float
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True


class PublicQuoteOut(BaseModel):
    code: str
    status: str
    subtotal: float
    itbis: float
    total: float
    created_at: datetime
    items: list[PublicQuoteItemOut]

    class Config:
        from_attributes = True


class PublicInvoiceOut(BaseModel):
    id: int
    code: str
    ncf: str | None
    subtotal: float
    itbis: float
    total: float
    created_at: datetime

    class Config:
        from_attributes = True


class PublicProjectOut(BaseModel):
    code: str
    status: str
    date: date
    description: str | None
    client_name: str
    quotes: list[PublicQuoteOut]
    invoices: list[PublicInvoiceOut]


class PublicLinkOut(BaseModel):
    token: str
