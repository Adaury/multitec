from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


def seed() -> None:
    settings = get_settings()
    db = SessionLocal()
    try:
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
