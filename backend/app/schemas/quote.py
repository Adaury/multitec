from datetime import datetime

from pydantic import BaseModel, Field


class QuoteItemIn(BaseModel):
    product_id: int | None = None
    description: str = Field(max_length=500)
    quantity: float = Field(default=1, gt=0)
    # None: no lo mandó el caller (usar precio del catálogo si hay producto, o 0 si es
    # texto libre) — distinto de un $0 explícito, que se respeta. Ver services/document_items.py.
    unit_price: float | None = Field(default=None, ge=0)
    note: str | None = Field(default=None, max_length=500)


class QuoteCreate(BaseModel):
    notes: str | None = Field(default=None, max_length=5000)
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
    note: str | None = None

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
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None
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
    reason: str = Field(max_length=2000)


class PurchaseListPreviewItem(BaseModel):
    product_id: int | None
    description: str
    quantity: float


class PurchaseListPreviewOut(BaseModel):
    """§ Motor 6 — lo que `build_material_rows_from_quote` generaría como `Material` si
    esta cotización se aprobara ahora. Solo lectura: no crea nada, para poder revisar la
    lista de compras antes de la aprobación."""

    quote_id: int
    already_generated: bool
    items: list[PurchaseListPreviewItem]
