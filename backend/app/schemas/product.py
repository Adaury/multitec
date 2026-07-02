from pydantic import BaseModel


class ProductCreate(BaseModel):
    category: str
    name: str
    unit: str = "unidad"
    price: float = 0
    notes: str | None = None


class ProductUpdate(BaseModel):
    name: str | None = None
    unit: str | None = None
    price: float | None = None
    notes: str | None = None


class ProductOut(BaseModel):
    id: int
    code: str
    category: str
    name: str
    unit: str
    price: float
    notes: str | None

    class Config:
        from_attributes = True
