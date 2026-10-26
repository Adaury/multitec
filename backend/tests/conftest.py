import os
import tempfile

# Las variables de entorno deben quedar listas ANTES de importar cualquier módulo de la
# app: Settings() se evalúa una sola vez (lru_cache) en cuanto algo importa
# app.core.config, y app.db.session crea el engine a nivel de módulo.
_TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "multitec_test.db")
if os.path.exists(_TEST_DB_PATH):
    os.remove(_TEST_DB_PATH)

os.environ["DATABASE_URL"] = f"sqlite:///{_TEST_DB_PATH}"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="multitec_test_uploads_")
os.environ["JWT_SECRET"] = "test-secret-not-for-production"
os.environ["ADMIN_EMAIL"] = "admin@multitec.com"
os.environ["ADMIN_PASSWORD"] = "test-admin-password"
# Las pruebas no deben depender del .env real del desarrollador: sin correo de verdad ni destinatario
# de alertas propio (los tests de notificaciones esperan el correo de cada admin).
os.environ["SMTP_HOST"] = ""
os.environ["SMTP_PASSWORD"] = ""
os.environ["NOTIFICATION_EMAIL"] = ""

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import app.models  # noqa: E402,F401  registra todos los modelos en Base.metadata
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _setup_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists(_TEST_DB_PATH):
        os.remove(_TEST_DB_PATH)


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """Sin esto, el rate limit de /api/auth/login (10/min) se agota a mitad de la
    suite, ya que casi todos los tests hacen login al menos una vez."""
    from app.core import lockout, quota
    from app.core.limiter import limiter
    from app.services import generation_jobs

    limiter.reset()
    lockout.reset()  # el bloqueo por cuenta, la cuota de IA y los trabajos de generación son globales al proceso
    quota.reset()
    generation_jobs.reset()
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    """Cada test parte de una base vacía — se trunca todo después de correr."""
    yield
    db = SessionLocal(bypass_tenant=True)
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def _company_one(_clean_tables):
    """La empresa 1 (la original) existe en cada prueba: es la dueña de todo lo que se crea sin decir otra.
    Va después de `_clean_tables` para que su fila se borre junto con las demás al terminar."""
    from app.models.company import Company

    db = SessionLocal(bypass_tenant=True)
    try:
        db.add(Company(id=1, name="Multitec", slug="multitec"))
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    """Sesión de prueba: pertenece a la empresa 1, igual que la de una petición de un usuario de esa empresa."""
    db = SessionLocal(company_id=1)
    try:
        yield db
    finally:
        db.close()


def create_user(db, email: str, password: str, role: str, company_id: int = 1, is_platform_admin: bool = False) -> User:
    from app.db.tenant import tenant_bypass

    user = User(
        name=email.split("@")[0],
        email=email,
        hashed_password=hash_password(password),
        role=role,
        company_id=company_id,
        is_platform_admin=is_platform_admin,
    )
    # Si el usuario es de una empresa distinta a la de la sesión de prueba, se crea sin filtro (como lo haría el panel).
    with tenant_bypass(db) if db.info.get("company_id") != company_id else _nullcontext():
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


class _nullcontext:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_category(
    client: TestClient, headers: dict, name: str = "Cámaras", code_prefix: str | None = "CAM"
) -> dict:
    """Crea una categoría de catálogo de prueba y devuelve su fila (id, slug, etc.) —
    _clean_tables trunca todo entre tests, así que cada test que necesite un category_id
    para crear productos debe pedir la suya."""
    resp = client.post("/api/categories", json={"name": name, "code_prefix": code_prefix}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def make_project(client: TestClient, headers: dict, client_name: str = "Cliente de prueba") -> dict:
    """Crea un cliente + proyecto de prueba y devuelve el proyecto (con code, id, etc.)."""
    client_resp = client.post("/api/clients", json={"name": client_name}, headers=headers)
    assert client_resp.status_code == 201, client_resp.text
    project_resp = client.post(
        "/api/projects", json={"client_id": client_resp.json()["id"]}, headers=headers
    )
    assert project_resp.status_code == 201, project_resp.text
    return project_resp.json()


def assign_to_tecnico(db, project: dict, email: str = "tecnico@test.com") -> None:
    """Un técnico solo ve lo suyo (services/access.py): lo deja como responsable del proyecto, igual que
    haría la oficina al asignárselo."""
    from app.models.project import Project

    user = db.query(User).filter(User.email == email).one()
    db.query(Project).filter(Project.id == project["id"]).update({"responsible_id": user.id})
    db.commit()


def seed_ncf_sequence(
    db,
    ncf_type: str = "B02",
    range_start: int = 1,
    range_end: int = 99999999,
    expires_at=None,
    active: bool = True,
):
    """Crea una secuencia NCF de prueba — convert-to-invoice necesita una secuencia
    activa y vigente para el tipo correspondiente o falla con 400."""
    from datetime import date, timedelta

    from app.models.ncf_sequence import NcfSequence

    sequence = NcfSequence(
        ncf_type=ncf_type,
        description=f"Secuencia de prueba {ncf_type}",
        range_start=range_start,
        range_end=range_end,
        next_number=range_start,
        expires_at=expires_at or (date.today() + timedelta(days=365)),
        active=active,
    )
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence


@pytest.fixture
def admin_token(client, db_session):
    create_user(db_session, "admin@test.com", "adminpass123", "admin")
    resp = client.post("/api/auth/login", data={"username": "admin@test.com", "password": "adminpass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def oficina_token(client, db_session):
    create_user(db_session, "oficina@test.com", "oficinapass123", "oficina")
    resp = client.post("/api/auth/login", data={"username": "oficina@test.com", "password": "oficinapass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def tecnico_token(client, db_session):
    create_user(db_session, "tecnico@test.com", "tecnicopass123", "tecnico")
    resp = client.post("/api/auth/login", data={"username": "tecnico@test.com", "password": "tecnicopass123"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]
