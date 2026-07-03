from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.product import Product
from app.models.stock_movement import StockMovement
from app.models.user import User
from app.schemas.stock_movement import StockMovementCreate, StockMovementOut

router = APIRouter(tags=["inventory"])

allowed_roles = require_role("admin", "oficina")


def _get_product(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return product


@router.get("/api/products/{product_id}/stock-movements", response_model=list[StockMovementOut])
def list_stock_movements(product_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    _get_product(db, product_id)
    return (
        db.query(StockMovement)
        .filter(StockMovement.product_id == product_id)
        .order_by(StockMovement.created_at.desc(), StockMovement.id.desc())
        .all()
    )


@router.post(
    "/api/products/{product_id}/stock-movements",
    response_model=StockMovementOut,
    status_code=status.HTTP_201_CREATED,
)
def create_stock_movement(
    product_id: int,
    payload: StockMovementCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    product = _get_product(db, product_id)

    if payload.movement_type == "salida" and payload.quantity > float(product.stock_quantity):
        raise HTTPException(
            status_code=400,
            detail=(
                f"No hay suficiente stock: disponible {float(product.stock_quantity):g}, "
                f"se pidió sacar {payload.quantity:g}."
            ),
        )

    movement = StockMovement(
        product_id=product_id,
        movement_type=payload.movement_type,
        quantity=payload.quantity,
        reason=payload.reason,
        created_by=current_user.id,
    )
    if payload.movement_type == "entrada":
        product.stock_quantity = float(product.stock_quantity) + payload.quantity
    else:
        product.stock_quantity = float(product.stock_quantity) - payload.quantity

    db.add(movement)
    db.commit()
    db.refresh(movement)
    return movement
