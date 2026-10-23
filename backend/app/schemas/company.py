from pydantic import BaseModel, Field


class CompanyUpdate(BaseModel):
    """Un campo vacío (o null) vuelve al valor de `.env`."""

    name: str | None = Field(default=None, max_length=120)
    tagline: str | None = Field(default=None, max_length=160)
    representative: str | None = Field(default=None, max_length=120)
    rnc: str | None = Field(default=None, max_length=30)
    cedula: str | None = Field(default=None, max_length=30)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=60)
    email: str | None = Field(default=None, max_length=120)
    website: str | None = Field(default=None, max_length=120)
    bank_info: str | None = Field(default=None, max_length=1000)
    invoice_notes: str | None = Field(default=None, max_length=1000)


class CompanyOut(BaseModel):
    name: str
    tagline: str
    representative: str
    rnc: str
    cedula: str
    address: str
    phone: str
    email: str
    website: str
    bank_info: str
    invoice_notes: str
    has_logo: bool
