from datetime import datetime

from pydantic import BaseModel, Field


class CatalogRuleCreate(BaseModel):
    target_tag: str = Field(max_length=60)
    # gt=0: null significa "modo fijo" (§ ai_engine/rules.py expand_with_rules), y 0
    # rompería el cálculo de lotes (división por cero) — no es un valor válido.
    per_source_units: float | None = Field(default=None, gt=0)
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=200)


class CatalogRuleUpdate(BaseModel):
    target_tag: str | None = Field(default=None, max_length=60)
    # gt=0: null significa "modo fijo" (§ ai_engine/rules.py expand_with_rules), y 0
    # rompería el cálculo de lotes (división por cero) — no es un valor válido.
    per_source_units: float | None = Field(default=None, gt=0)
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
