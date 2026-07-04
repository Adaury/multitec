import re
import unicodedata

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.product import Product
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate

router = APIRouter(prefix="/api/categories", tags=["categories"])

read_roles = require_role("admin", "oficina", "tecnico")
admin_only = require_role("admin")


def _slugify(name: str) -> str:
    """Slug ascii simple (sin librería externa): quita acentos, minúsculas, guiones."""
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", normalized.lower()).strip("-")
    return slug or "categoria"


def _unique_slug(db: Session, base_slug: str, exclude_id: int | None = None) -> str:
    slug = base_slug
    suffix = 2
    while True:
        query = db.query(Category).filter(Category.slug == slug)
        if exclude_id is not None:
            query = query.filter(Category.id != exclude_id)
        if query.one_or_none() is None:
            return slug
        slug = f"{base_slug}-{suffix}"
        suffix += 1


def _get_category(db: Session, category_id: int) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    return category


@router.get("", response_model=list[CategoryOut])
def list_categories(db: Session = Depends(get_db), _=Depends(read_roles)):
    return db.query(Category).order_by(Category.name).all()


@router.post("", response_model=CategoryOut, status_code=201)
def create_category(payload: CategoryCreate, db: Session = Depends(get_db), _=Depends(admin_only)):
    if payload.parent_id is not None:
        _get_category(db, payload.parent_id)

    slug = _unique_slug(db, _slugify(payload.name))
    category = Category(
        name=payload.name, slug=slug, code_prefix=payload.code_prefix or None, parent_id=payload.parent_id
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(
    category_id: int, payload: CategoryUpdate, db: Session = Depends(get_db), _=Depends(admin_only)
):
    category = _get_category(db, category_id)

    if payload.parent_id is not None:
        if payload.parent_id == category_id:
            raise HTTPException(status_code=400, detail="Una categoría no puede ser su propio padre")
        new_parent = _get_category(db, payload.parent_id)
        node = new_parent
        while node is not None:
            if node.id == category_id:
                raise HTTPException(status_code=400, detail="No se puede crear un ciclo en el árbol de categorías")
            node = node.parent

    data = payload.model_dump(exclude_unset=True)
    if "name" in data and data["name"] != category.name:
        category.slug = _unique_slug(db, _slugify(data["name"]), exclude_id=category.id)
    for field, value in data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=204)
def delete_category(category_id: int, db: Session = Depends(get_db), _=Depends(admin_only)):
    category = _get_category(db, category_id)

    if db.query(Category).filter(Category.parent_id == category_id).first() is not None:
        raise HTTPException(status_code=400, detail="No se puede eliminar: tiene subcategorías")
    if db.query(Product).filter(Product.category_id == category_id).first() is not None:
        raise HTTPException(status_code=400, detail="No se puede eliminar: hay productos con esta categoría")

    db.delete(category)
    db.commit()
