from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class ProductCreate(BaseModel):
    category: str = Field(max_length=100)
    name: str = Field(max_length=255)
    unit: str = Field(default="unidad", max_length=30)
    price: float = 0
    notes: str | None = Field(default=None, max_length=2000)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    commercial_description: str | None = Field(default=None, max_length=2000)
    technical_description: str | None = Field(default=None, max_length=2000)
    tags: list[str] = []
    synonyms: list[str] = []
    suggests_tags: list[str] = []


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    unit: str | None = Field(default=None, max_length=30)
    price: float | None = None
    notes: str | None = Field(default=None, max_length=2000)
    brand: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    commercial_description: str | None = Field(default=None, max_length=2000)
    technical_description: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = None
    synonyms: list[str] | None = None
    suggests_tags: list[str] | None = None


class ProductOut(BaseModel):
    id: int
    code: str
    category: str
    name: str
    unit: str
    price: float
    stock_quantity: float
    notes: str | None
    brand: str | None = None
    model: str | None = None
    commercial_description: str | None = None
    technical_description: str | None = None
    tags: list[str] = []
    synonyms: list[str] = []
    suggests_tags: list[str] = []
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True

    @field_validator("tags", "synonyms", "suggests_tags", mode="before")
    @classmethod
    def _null_list_to_empty(cls, v):
        """Las columnas son JSON nullable — filas viejas/sin etiquetar tienen NULL, no []."""
        return v or []
