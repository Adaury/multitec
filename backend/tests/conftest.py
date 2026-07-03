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
def _clean_tables():
    """Cada test parte de una base vacía — se trunca todo después de correr."""
    yield
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_user(db, email: str, password: str, role: str) -> User:
    user = User(name=email.split("@")[0], email=email, hashed_password=hash_password(password), role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_project(client: TestClient, headers: dict, client_name: str = "Cliente de prueba") -> dict:
    """Crea un cliente + proyecto de prueba y devuelve el proyecto (con code, id, etc.)."""
    client_resp = client.post("/api/clients", json={"name": client_name}, headers=headers)
    assert client_resp.status_code == 201, client_resp.text
    project_resp = client.post(
        "/api/projects", json={"client_id": client_resp.json()["id"]}, headers=headers
    )
    assert project_resp.status_code == 201, project_resp.text
    return project_resp.json()


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
