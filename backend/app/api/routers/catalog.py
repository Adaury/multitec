from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.catalog_rule import CatalogRule
from app.models.product import Product, resolve_code_prefix
from app.models.technical_rule import TechnicalRule
from app.models.user import User
from app.schemas.catalog_rule import CatalogRuleCreate, CatalogRuleOut, CatalogRuleUpdate
from app.schemas.product import ProductCreate, ProductOut, ProductUpdate
from app.schemas.technical_rule import TechnicalRuleCreate, TechnicalRuleOut, TechnicalRuleUpdate
from app.services.code_generator import next_code

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


def _get_category_or_404(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=400, detail=f"Categoría desconocida: {category_id}")
    return category


@router.get("", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Product).order_by(Product.code).all()


@router.post("", response_model=ProductOut, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)):
    category = _get_category_or_404(db, payload.category_id)

    code = next_code(db, resolve_code_prefix(category))
    product = Product(code=code, created_by=current_user.id, **payload.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/{product_id}", response_model=ProductOut)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db), _=Depends(admin_only)):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "category_id" in data and data["category_id"] is not None:
        _get_category_or_404(db, data["category_id"])
    for field, value in data.items():
        setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.get("/{product_id}/rules", response_model=list[CatalogRuleOut])
def list_rules(product_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(CatalogRule).filter(CatalogRule.source_product_id == product_id).order_by(CatalogRule.id).all()


@router.post("/{product_id}/rules", response_model=CatalogRuleOut, status_code=status.HTTP_201_CREATED)
def create_rule(
    product_id: int, payload: CatalogRuleCreate, db: Session = Depends(get_db), _=Depends(admin_only)
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    rule = CatalogRule(source_product_id=product_id, **payload.model_dump())
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/rules/{rule_id}", response_model=CatalogRuleOut)
def update_rule(rule_id: int, payload: CatalogRuleUpdate, db: Session = Depends(get_db), _=Depends(admin_only)):
    rule = db.get(CatalogRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rule, field, value)
    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    rule = db.get(CatalogRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    db.delete(rule)
    db.commit()


@router.get("/{product_id}/technical-rules", response_model=list[TechnicalRuleOut])
def list_technical_rules(product_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(TechnicalRule)
        .filter(TechnicalRule.source_product_id == product_id)
        .order_by(TechnicalRule.id)
        .all()
    )


@router.post(
    "/{product_id}/technical-rules", response_model=TechnicalRuleOut, status_code=status.HTTP_201_CREATED
)
def create_technical_rule(
    product_id: int, payload: TechnicalRuleCreate, db: Session = Depends(get_db), _=Depends(admin_only)
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    rule = TechnicalRule(
        source_product_id=product_id,
        action_type=payload.action_type,
        action_params={
            "target_tag": payload.target_tag,
            "per_source_units": payload.per_source_units,
            "quantity": payload.quantity,
        },
        notes=payload.notes,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.put("/technical-rules/{rule_id}", response_model=TechnicalRuleOut)
def update_technical_rule(
    rule_id: int, payload: TechnicalRuleUpdate, db: Session = Depends(get_db), _=Depends(admin_only)
):
    rule = db.get(TechnicalRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")

    data = payload.model_dump(exclude_unset=True)
    if "notes" in data:
        rule.notes = data.pop("notes")
    if data:
        rule.action_params = {**rule.action_params, **data}

    db.commit()
    db.refresh(rule)
    return rule


@router.delete("/technical-rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_technical_rule(rule_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    rule = db.get(TechnicalRule, rule_id)
    if rule is None:
        raise HTTPException(status_code=404, detail="Regla no encontrada")
    db.delete(rule)
    db.commit()
