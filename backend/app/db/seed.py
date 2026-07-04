from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.db.taxonomy import TAXONOMY
from app.models.category import Category
from app.models.user import User


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


def seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
        seed_categories(db)

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
