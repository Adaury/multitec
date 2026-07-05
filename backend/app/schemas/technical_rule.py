from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TechnicalRuleCreate(BaseModel):
    """Hoy solo existe el tipo de acción "add_accessory" (agregar un accesorio del
    catálogo por cantidad — igual que `CatalogRule`), de ahí que target_tag/
    per_source_units/quantity vengan como campos planos en vez de un `action_params`
    genérico en esta capa. Cuando se agregue un segundo tipo de acción (Motor 5/6), este
    esquema pasa a ser una unión discriminada por `action_type`; la tabla ya lo soporta
    (`action_params` es JSON) sin necesitar migración."""

    action_type: Literal["add_accessory"] = "add_accessory"
    target_tag: str = Field(max_length=60)
    per_source_units: float | None = None
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=200)


class TechnicalRuleUpdate(BaseModel):
    target_tag: str | None = Field(default=None, max_length=60)
    per_source_units: float | None = None
    quantity: float | None = None
    notes: str | None = Field(default=None, max_length=200)


class TechnicalRuleOut(BaseModel):
    id: int
    source_product_id: int
    action_type: str
    target_tag: str | None
    per_source_units: float | None
    quantity: float
    notes: str | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
