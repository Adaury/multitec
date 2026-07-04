from datetime import datetime

from pydantic import BaseModel, Field


class CatalogRuleCreate(BaseModel):
    target_tag: str = Field(max_length=60)
    per_source_units: float | None = None
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=200)


class CatalogRuleUpdate(BaseModel):
    target_tag: str | None = Field(default=None, max_length=60)
    per_source_units: float | None = None
    quantity: float | None = None
    notes: str | None = Field(default=None, max_length=200)


class CatalogRuleOut(BaseModel):
    id: int
    source_product_id: int
    target_tag: str
    per_source_units: float | None
    quantity: float
    notes: str | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
