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
    id: int
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


class PublicTicketOut(BaseModel):
    code: str
    problem: str
    solution: str | None
    status: str
    technician_name: str | None
    created_at: datetime
    resolved_at: datetime | None

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
    tickets: list[PublicTicketOut]


class PublicLinkOut(BaseModel):
    token: str
