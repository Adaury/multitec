from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RelationType = Literal["compatible_con", "alternativa_de", "requiere"]


class ProductRelationCreate(BaseModel):
    related_product_id: int
    relation_type: RelationType
    notes: str | None = Field(default=None, max_length=200)


class ProductRelationUpdate(BaseModel):
    relation_type: RelationType | None = None
    notes: str | None = Field(default=None, max_length=200)


class ProductRelationOut(BaseModel):
    """Forma cruda de la fila (tal como se guardó) — la devuelven crear/actualizar/borrar,
    donde `product_id` siempre es el producto de la URL, sin ambigüedad de dirección."""

    id: int
    product_id: int
    related_product_id: int
    relation_type: str
    notes: str | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class ProductRelationView(BaseModel):
    """Vista normalizada para listar las relaciones de un producto — `related_product_id`
    siempre es "el otro producto" sin importar de qué lado se guardó la fila, y
    `direction` distingue si este producto declaró la relación (`outgoing`) o si la
    relación la declaró el otro producto sobre este (`incoming`)."""

    id: int
    relation_type: str
    direction: Literal["outgoing", "incoming"]
    related_product_id: int
    related_product_name: str | None
    notes: str | None
    created_at: datetime | None = None
