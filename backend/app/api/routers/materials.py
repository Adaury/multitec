from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.material import MATERIAL_STATUSES, Material
from app.models.product import Product
from app.schemas.material import MaterialCreate, MaterialOut, MaterialStatusUpdate

router = APIRouter(tags=["materials"])

allowed_roles = require_role("admin", "oficina")


@router.get("/api/projects/{project_id}/materials", response_model=list[MaterialOut])
def list_materials(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Material)
        .filter(Material.project_id == project_id)
        .order_by(Material.created_at.desc())
        .all()
    )


@router.get("/api/projects/{project_id}/materials/purchase-list", response_model=list[MaterialOut])
def purchase_list(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Lista inteligente de compras (§10) — materiales pendientes de comprar."""
    return (
        db.query(Material)
        .filter(Material.project_id == project_id, Material.status == "pendiente_compra")
        .order_by(Material.created_at)
        .all()
    )


@router.post("/api/projects/{project_id}/materials", response_model=MaterialOut, status_code=201)
def create_material(project_id: int, payload: MaterialCreate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    description = payload.description
    if payload.product_id is not None:
        product = db.get(Product, payload.product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Producto {payload.product_id} no encontrado")
        description = description or product.name

    material = Material(
        project_id=project_id,
        product_id=payload.product_id,
        description=description,
        quantity=payload.quantity,
        notes=payload.notes,
        status="pendiente_compra",
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.put("/api/materials/{material_id}/status", response_model=MaterialOut)
def update_material_status(
    material_id: int, payload: MaterialStatusUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    if payload.status not in MATERIAL_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {payload.status}")
    material = db.get(Material, material_id)
    if material is None:
        raise HTTPException(status_code=404, detail="Material no encontrado")
    material.status = payload.status
    db.commit()
    db.refresh(material)
    return material
