"""Aislamiento entre empresas: lo que crea la empresa A no existe para la empresa B, por ninguna ruta.

Dos niveles: (1) la sesión (TenantSession) por sí sola, y (2) la API entera, recorriendo TODAS las rutas GET con
el token de B contra los ids de A."""

import re

import pytest

from app.db.session import SessionLocal
from app.db.tenant import TenantContextError, tenant_bypass
from app.main import app
from app.models.client import Client
from app.models.company import Company
from tests.conftest import auth_headers, create_user, make_category, make_project

MARKER = "SECRETO-EMPRESA-A"
# Rutas que no son "datos de una empresa" o que no llevan sesión de empresa.
SKIP_PREFIXES = ("/api/auth", "/api/public", "/api/platform", "/uploads", "/docs", "/openapi", "/redoc", "/api/health")


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.fixture
def two_companies(client, db_session):
    """Empresa 1 (A) con datos reconocibles y empresa 2 (B) vacía, cada una con su administrador."""
    with tenant_bypass(db_session):
        db_session.add(Company(id=2, name="Empresa B", slug="empresa-b"))
        db_session.commit()
    create_user(db_session, "a@test.com", "passwordA-1234", "admin", company_id=1)
    create_user(db_session, "b@test.com", "passwordB-1234", "admin", company_id=2)
    a = auth_headers(_login(client, "a@test.com", "passwordA-1234"))
    b = auth_headers(_login(client, "b@test.com", "passwordB-1234"))
    category = make_category(client, a)
    client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": f"{MARKER} producto", "unit": "ud", "price": 100, "cost": 50},
        headers=a,
    )
    project = make_project(client, a, client_name=f"{MARKER} cliente")
    # Más datos en A (todos con id 1 en su tabla): si solo hubiera cliente y proyecto, casi toda la prueba vería «404
    # porque no existe» y no «404 porque es de otra empresa».
    client.post("/api/suppliers", json={"name": f"{MARKER} proveedor"}, headers=a)
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": f"{MARKER} cámara", "quantity": 2, "unit_price": 100}]},
        headers=a,
    ).json()
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=a)
    client.post(f"/api/projects/{project['id']}/tickets", json={"problem": f"{MARKER} falla"}, headers=a)
    client.post(
        f"/api/projects/{project['id']}/logbook", json={"comment": f"{MARKER} bitácora", "entry_date": "2026-10-27"}, headers=a
    )
    return a, b, project


# ---------------------------------------------------------------- la sesión por sí sola


def test_session_without_company_fails_closed(two_companies):
    with SessionLocal() as db:
        with pytest.raises(TenantContextError):
            db.query(Client).all()


def test_session_only_sees_its_own_company(two_companies):
    with SessionLocal(company_id=2) as db:
        assert db.query(Client).count() == 0
        assert db.get(Client, 1) is None  # un id de otra empresa no se puede traer ni por llave primaria
    with SessionLocal(company_id=1) as db:
        assert db.query(Client).count() == 1


def test_session_stamps_company_and_rejects_foreign_objects(two_companies):
    with SessionLocal(company_id=2) as db:
        db.add(Client(name="de B"))
        db.commit()
        assert db.query(Client).one().company_id == 2
        db.add(Client(name="intruso", company_id=1))
        with pytest.raises(Exception):
            db.commit()


def test_same_code_allowed_in_two_companies(client, two_companies):
    a, b, project = two_companies
    other = make_project(client, b, client_name="Cliente de B")
    assert other["code"] == project["code"]  # cada empresa lleva su propia numeración


# ---------------------------------------------------------------- toda la API


def _operations(*methods: str) -> list[tuple[str, str]]:
    """Todas las operaciones reales de la API, sacadas del esquema OpenAPI. (No se recorre `app.routes`: en esta versión
    de FastAPI los routers incluidos vienen anidados y ese recorrido solo veía 2 rutas, o sea que la prueba no probaba
    nada.)"""
    found = []
    for path, ops in app.openapi()["paths"].items():
        if path.startswith(SKIP_PREFIXES):
            continue
        for method in ops:
            if method.upper() in methods:
                found.append((method.upper(), path))
    return sorted(found)


def _fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def _has_content(value) -> bool:
    """True si la respuesta trae algo: una lista vacía, un objeto de valores vacíos o ceros no cuenta."""
    if isinstance(value, dict):
        return any(_has_content(v) for v in value.values())
    if isinstance(value, list):
        return any(_has_content(v) for v in value)
    return value not in (None, "", 0, 0.0, False)


def test_the_route_walk_really_covers_the_whole_api():
    gets = _operations("GET")
    assert len(gets) >= 60, f"solo se encontraron {len(gets)} rutas GET: el recorrido no está viendo toda la API"
    assert ("GET", "/api/projects/{project_id}") in gets and ("GET", "/api/quotes/{quote_id}") in gets
    assert len(_operations("PUT", "PATCH", "DELETE", "POST")) >= 90


def test_every_get_route_hides_company_a_from_company_b(client, two_companies):
    a, b, _project = two_companies
    leaks, with_id_checked, real_data = [], 0, 0
    for _method, path in _operations("GET"):
        url = _fill(path)
        with_id = "{" in path
        # La empresa B, con los ids de A (todo en A empieza en 1), jamás debe recibir datos.
        resp = client.get(url, headers=b)
        if MARKER in resp.text:
            leaks.append(f"{url}: contiene datos de A")
        # Un listado «de un proyecto» con el id de otra empresa puede responder 200 con la lista vacía (igual que para un
        # id que no existe: no revela nada). Lo que no puede es traer contenido.
        elif with_id and resp.status_code == 200 and _has_content(resp.json()):
            leaks.append(f"{url}: respondió con datos a un id de otra empresa")
        if with_id:
            with_id_checked += 1
            # Control: la propia empresa A sí ve ese mismo id (si no, la prueba solo vería 404 por no existir)
            real_data += client.get(url, headers=a).status_code == 200
    assert not leaks, "\n".join(leaks)
    assert with_id_checked >= 40
    assert real_data >= 6, f"solo {real_data} rutas con id devolvieron datos a la empresa A: los datos de prueba no alcanzan"


def test_no_write_operation_succeeds_for_company_b_on_company_a_ids(client, two_companies):
    """PUT / PATCH / DELETE / POST sobre ids de A con el token de B: ninguna debe terminar en 2xx."""
    a, b, _project = two_companies
    succeeded = []
    for method, path in _operations("PUT", "PATCH", "DELETE", "POST"):
        if "{" not in path:
            continue  # sin id no apunta a datos de A (crear algo propio es legítimo)
        resp = client.request(method, _fill(path), json={}, headers=b)
        if resp.status_code < 300:
            succeeded.append(f"{method} {path} -> {resp.status_code}")
    assert not succeeded, "\n".join(succeeded)


def test_company_b_lists_are_empty(client, two_companies):
    a, b, _project = two_companies
    for url in ("/api/clients", "/api/projects", "/api/catalog"):
        assert client.get(url, headers=b).json() == [], url
        assert client.get(url, headers=a).json() != [], url


def test_company_b_cannot_modify_company_a(client, two_companies):
    a, b, project = two_companies
    assert client.put(f"/api/projects/{project['id']}", json={"notes": "hackeado"}, headers=b).status_code in (404, 405)
    assert client.delete(f"/api/clients/{project['client_id']}", headers=b).status_code in (404, 405)
    # Y B no puede colgar su proyecto de un cliente de A
    resp = client.post("/api/projects", json={"client_id": project["client_id"]}, headers=b)
    assert resp.status_code in (400, 404, 422)


def test_aggregates_and_subqueries_are_scoped_too(two_companies):
    """`Query.count()` y `select(func.count()).select_from(Modelo)` no traen columnas de la entidad: el filtro por
    empresa tiene que aplicarse igual (fue un hueco real)."""
    from sqlalchemy import func, select

    with SessionLocal(company_id=2) as db:
        assert db.query(Client).count() == 0
        assert db.query(func.count(Client.id)).scalar() == 0
        assert db.execute(select(func.count()).select_from(Client)).scalar() == 0
        assert db.execute(select(select(func.count()).select_from(Client).scalar_subquery())).scalar() == 0


ITEM = {"description": "x", "quantity": 1, "unit_price": 1}
# Crear algo «dentro de un proyecto» con el id del proyecto de OTRA empresa, con cuerpos válidos (con cuerpo vacío la
# validación responde 422 antes de llegar a la lógica y la prueba no vería nada).
CREATE_ON_PROJECT = {
    "/api/projects/{id}/budgets": {"items": [ITEM]},
    "/api/projects/{id}/quotes": {"items": [ITEM]},
    "/api/projects/{id}/pre-invoices": {"items": [ITEM]},
    "/api/projects/{id}/tickets": {"problem": "x"},
    "/api/projects/{id}/logbook": {"comment": "x", "entry_date": "2026-10-27"},
    "/api/projects/{id}/extensions": {"title": "x"},
    "/api/projects/{id}/materials": {"description": "x", "quantity": 1},
}


def test_company_b_cannot_create_anything_hanging_from_a_project_of_company_a(client, two_companies):
    a, b, project = two_companies
    for template, body in CREATE_ON_PROJECT.items():
        resp = client.post(template.replace("{id}", str(project["id"])), json=body, headers=b)
        assert resp.status_code == 404, f"{template}: {resp.status_code} {resp.text[:120]}"
    resp = client.post("/api/visits", json={"project_id": project["id"], "scheduled_date": "2026-11-01"}, headers=b)
    assert resp.status_code == 404, f"/api/visits: {resp.status_code} {resp.text[:120]}"
    # Y no quedó nada de B colgando del proyecto de A
    from app.models.budget import Budget
    from app.models.quote import Quote
    from app.models.ticket import Ticket

    with SessionLocal(bypass_tenant=True) as db:
        for model in (Quote, Budget, Ticket):
            assert db.query(model).filter(model.company_id == 2).count() == 0, model.__name__


def test_the_session_refuses_a_row_that_points_to_another_company(two_companies):
    from app.db.tenant import TenantReferenceError
    from app.models.project import Project

    with SessionLocal(company_id=2) as db:
        db.add(Project(client_id=1, code="PRY-X"))  # el cliente 1 es de la empresa A
        with pytest.raises(TenantReferenceError):
            db.commit()
    with SessionLocal(company_id=1) as db:
        db.add(Project(client_id=1, code="PRY-OK"))  # el mismo cliente, desde su empresa, sí
        db.commit()


def test_company_b_admin_cannot_revoke_sessions_of_company_a_users(client, two_companies):
    a, b, _project = two_companies
    # A tiene una sesión (la del login de su admin): B no puede cerrarla, ni sabiendo los ids
    from app.models.refresh_token import RefreshToken

    with SessionLocal(bypass_tenant=True) as db:
        token = db.query(RefreshToken).filter(RefreshToken.revoked.is_(False)).order_by(RefreshToken.id).first()
        user_id, session_id = token.user_id, token.id
    resp = client.delete(f"/api/users/{user_id}/sessions/{session_id}", headers=b)
    assert resp.status_code == 404
    with SessionLocal(bypass_tenant=True) as db:
        assert db.get(RefreshToken, session_id).revoked is False
