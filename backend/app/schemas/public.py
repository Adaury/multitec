from datetime import date, datetime

from pydantic import BaseModel, Field


class PublicApproveIn(BaseModel):
    """Quién aprueba (el cliente escribe su nombre: queda en el historial como constancia)."""

    signer_name: str | None = Field(default=None, max_length=120)


class PublicRejectIn(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)
    signer_name: str | None = Field(default=None, max_length=120)


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
