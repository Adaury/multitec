from datetime import datetime

from pydantic import BaseModel, Field


class MaterialCreate(BaseModel):
    product_id: int | None = None
    description: str = Field(max_length=500)
    quantity: float = 1
    notes: str | None = Field(default=None, max_length=2000)


class MaterialStatusUpdate(BaseModel):
    status: str = Field(max_length=30)
    # Quién lo vendió y a qué precio real (distinto de Product.price/cost, que son
    # estimados de catálogo) — opcionales, se pueden completar en cualquier transición de
    # estado, no solo al marcar "comprado".
    supplier_id: int | None = None
    purchase_price: float | None = None


class MaterialOut(BaseModel):
    id: int
    project_id: int
    product_id: int | None
    source_quote_id: int | None
    description: str
    quantity: float
    status: str
    notes: str | None
    supplier_id: int | None = None
    purchase_price: float | None = None
    supplier_name: str | None = None
    created_by: int | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


class SupplierPurchaseOut(MaterialOut):
    """Historial de compras de un proveedor — mismo shape que MaterialOut más el proyecto
    de origen, ya que un proveedor puede vender a materiales de varios proyectos."""

    project_code: str
