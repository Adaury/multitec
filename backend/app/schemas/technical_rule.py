from datetime import datetime
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field


class AddAccessoryCreate(BaseModel):
    """Acción original: agregar un accesorio del catálogo por cantidad — igual que
    `CatalogRule`. `target_tag`/`per_source_units`/`quantity` van planos (no en un
    `action_params` genérico) porque a este nivel de API cada acción tiene su propia
    forma; la tabla sigue guardando `action_params` como JSON sin importar cuál sea."""

    action_type: Literal["add_accessory"] = "add_accessory"
    target_tag: str = Field(max_length=60)
    per_source_units: float | None = None
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=200)


class SetCalculationParameterCreate(BaseModel):
    """Motor 4 → Motor 5: mientras `source_product_id` esté presente en el presupuesto,
    `parameter_key` se sobreescribe a `value` solo para esa generación — no persiste en
    `calculation_parameters` (ese sigue siendo el default global). Ej.: "si hay fibra
    óptica, el margen de desperdicio de cable sube a 8%"."""

    action_type: Literal["set_calculation_parameter"] = "set_calculation_parameter"
    parameter_key: str = Field(max_length=60)
    value: float
    notes: str | None = Field(default=None, max_length=200)


class FlagEngineeringNoteCreate(BaseModel):
    """Motor 4 → Motor 6: mientras `source_product_id` esté presente en el presupuesto,
    `engineering_note` se agrega al borrador de ingeniería generado por IA (solo si el
    borrador se generó en esta corrida — no pisa ingeniería ya escrita a mano). Ej.: "si
    hay fibra monomodo, agregar 'Verificar distancia máxima de fibra monomodo.'"."""

    action_type: Literal["flag_engineering_note"] = "flag_engineering_note"
    engineering_note: str = Field(max_length=500)
    notes: str | None = Field(default=None, max_length=200)


TechnicalRuleCreate = Annotated[
    Union[AddAccessoryCreate, SetCalculationParameterCreate, FlagEngineeringNoteCreate],
    Field(discriminator="action_type"),
]


class TechnicalRuleUpdate(BaseModel):
    """No cambia `action_type` (igual que `CatalogRule` no permite cambiar el producto
    fuente) — solo los parámetros propios de la acción que la regla ya tenía. El router
    aplica cualquiera de estos campos que venga, sin exigir que combinen con el
    `action_type` de la fila (igual de permisivo que hoy)."""

    target_tag: str | None = Field(default=None, max_length=60)
    per_source_units: float | None = None
    quantity: float | None = None
    parameter_key: str | None = Field(default=None, max_length=60)
    value: float | None = None
    engineering_note: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=200)


class TechnicalRuleOut(BaseModel):
    id: int
    source_product_id: int
    action_type: str
    target_tag: str | None
    per_source_units: float | None
    quantity: float
    parameter_key: str | None
    value: float | None
    engineering_note: str | None
    notes: str | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
