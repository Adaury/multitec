"""Aislamiento entre empresas: lo que crea la empresa A no existe para la empresa B, por ninguna ruta.

Dos niveles: (1) la sesión (TenantSession) por sí sola, y (2) la API entera, recorriendo TODAS las rutas GET con
el token de B contra los ids de A."""

import re

import pytest
from fastapi.routing import APIRoute

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


def _get_routes():
    routes = []
    for route in app.routes:
        if not isinstance(route, APIRoute) or "GET" not in route.methods:
            continue
        if route.path.startswith(SKIP_PREFIXES):
            continue
        routes.append(route)
    return routes


def _fill(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "1", path)


def test_every_get_route_hides_company_a_from_company_b(client, two_companies):
    a, b, _project = two_companies
    leaks = []
    for route in _get_routes():
        url = _fill(route.path)
        with_id = "{" in route.path
        # La empresa B, con los ids de A (todo en A empieza en 1), jamás debe recibir datos.
        resp = client.get(url, headers=b)
        body = resp.text
        if MARKER in body:
            leaks.append(f"{url}: contiene datos de A")
        elif with_id and resp.status_code == 200:
            leaks.append(f"{url}: respondió 200 a un id de otra empresa")
    assert not leaks, "\n".join(leaks)


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
