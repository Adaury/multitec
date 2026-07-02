from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.product import CATEGORY_PREFIXES, Product
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.services.code_generator import next_code

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Product).order_by(Product.code).all()


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), _=Depends(admin_only)):
    prefix = CATEGORY_PREFIXES.get(payload.category)
    if prefix is None:
        raise HTTPException(status_code=400, detail=f"Categoría desconocida: {payload.category}")

    code = next_code(db, prefix)
    product = Product(code=code, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), _=Depends(admin_only)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product
