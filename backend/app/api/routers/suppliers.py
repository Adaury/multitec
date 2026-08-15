from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.material import Material
from app.models.supplier import Supplier
from app.models.user import User
from app.schemas.material import SupplierPurchaseOut
from app.schemas.supplier import SupplierCreate, SupplierOut, SupplierUpdate

router = APIRouter(prefix="/api/suppliers", tags=["suppliers"])

# Compras/Catálogo no son del rol tecnico (ver materials.py/catalog.py) — proveedores
# tampoco.
allowed_roles = require_role("admin", "oficina")


@router.get("", response_model=list[SupplierOut])
def list_suppliers(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Supplier).order_by(Supplier.name).all()


@router.post("", response_model=SupplierOut, status_code=status.HTTP_201_CREATED)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    supplier = Supplier(**payload.model_dump(), created_by=current_user.id)
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}", response_model=SupplierOut)
def get_supplier(supplier_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return supplier


@router.put("/{supplier_id}", response_model=SupplierOut)
def update_supplier(supplier_id: int, payload: SupplierUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for field, value in payload.model_dump().items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


@router.get("/{supplier_id}/materials", response_model=list[SupplierPurchaseOut])
def list_supplier_purchases(supplier_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    supplier = db.get(Supplier, supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return (
        db.query(Material)
        .options(joinedload(Material.project), joinedload(Material.supplier))
        .filter(Material.supplier_id == supplier_id)
        .order_by(Material.updated_at.desc(), Material.created_at.desc())
        .all()
    )
