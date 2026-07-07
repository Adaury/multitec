from app.core.config import get_settings
from app.core.security import hash_password
from app.db.product_catalog_seed import PRODUCT_CATALOG_SEED
from app.db.session import SessionLocal
from app.db.taxonomy import TAXONOMY
from app.models.category import Category
from app.models.product import Product, resolve_code_prefix
from app.models.user import User
from app.services.code_generator import next_code


def seed_categories(db) -> None:
    """Top-up idempotente del árbol de clasificaciones (§ catálogo inteligente v2): crea
    las categorías/subcategorías de app/db/taxonomy.py que todavía no existan por slug —
    no toca las que ya están (el admin puede haberlas renombrado o reordenado)."""
    existing_slugs = {slug for (slug,) in db.query(Category.slug).all()}

    def insert_node(node: dict, parent_id: int | None) -> None:
        if node["slug"] in existing_slugs:
            category = db.query(Category).filter(Category.slug == node["slug"]).one()
            category_id = category.id
        else:
            category = Category(
                name=node["name"], slug=node["slug"], code_prefix=node.get("code_prefix"), parent_id=parent_id
            )
            db.add(category)
            db.flush()
            category_id = category.id
            existing_slugs.add(node["slug"])
        for child in node.get("children", []):
            insert_node(child, category_id)

    for root in TAXONOMY:
        insert_node(root, None)
    db.commit()


def seed_products(db) -> None:
    """Top-up idempotente del catálogo base (§ catálogo inteligente v2): crea los productos
    de app/db/product_catalog_seed.py que todavía no existan por nombre — no toca los que
    ya están (el admin puede haberles cambiado precio, tags, etc). Genera el code igual que
    POST /catalog (next_code sobre el prefijo de la categoría) para no chocar con productos
    creados a mano."""
    existing_names = {name for (name,) in db.query(Product.name).all()}

    for item in PRODUCT_CATALOG_SEED:
        if item["name"] in existing_names:
            continue
        category = db.query(Category).filter(Category.slug == item["category_slug"]).one()
        code = next_code(db, resolve_code_prefix(category))
        product = Product(
            code=code,
            category_id=category.id,
            name=item["name"],
            unit=item["unit"],
            price=item["price"],
            cost=item.get("cost", 0),
            resolution_mp=item.get("resolution_mp"),
            channel_capacity=item.get("channel_capacity"),
            tags=item.get("tags"),
            synonyms=item.get("synonyms"),
        )
        db.add(product)
        existing_names.add(item["name"])
    db.commit()


def seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        seed_categories(db)
        seed_products(db)

        existing = db.query(User).filter(User.email == settings.admin_email).one_or_none()
        if existing is not None:
            print(f"El usuario admin '{settings.admin_email}' ya existe. No se creó de nuevo.")
            return

        admin = User(
            name=settings.admin_name,
            email=settings.admin_email,
            hashed_password=hash_password(settings.admin_password),
            role="admin",
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print(f"Usuario admin creado: {settings.admin_email}")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
