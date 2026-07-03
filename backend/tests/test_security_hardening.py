import io

from app.core.limiter import limiter
from tests.conftest import auth_headers, create_user, make_project


def test_login_rate_limited_after_too_many_attempts(client, db_session):
    limiter.reset()
    create_user(db_session, "brute@test.com", "correctpass123", "oficina")

    responses = [
        client.post("/api/auth/login", data={"username": "brute@test.com", "password": "wrongpass"})
        for _ in range(15)
    ]
    statuses = [r.status_code for r in responses]

    assert 401 in statuses  # las primeras fallan por credenciales, normal
    assert 429 in statuses  # a partir de cierto punto, el rate limit corta


def test_oversized_survey_photo_rejected(client, admin_token, monkeypatch):
    from app.core.config import get_settings

    # get_settings() está cacheado (lru_cache) y devuelve siempre la misma instancia;
    # mutar el atributo alcanza a todas las llamadas futuras dentro del proceso.
    # monkeypatch restaura el valor original automáticamente al terminar el test.
    monkeypatch.setattr(get_settings(), "max_upload_mb", 0)  # cualquier archivo excede 0 MB

    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    files = {"file": ("foto.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 100), "image/png")}
    resp = client.post(
        f"/api/projects/{project['id']}/survey/assets",
        data={"kind": "photo"},
        files=files,
        headers=headers,
    )
    assert resp.status_code == 413


def test_client_name_over_max_length_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.post("/api/clients", json={"name": "x" * 200}, headers=headers)
    assert resp.status_code == 422


def test_unhandled_exception_returns_generic_500_without_leaking_details(admin_token):
    from fastapi.testclient import TestClient

    from app.db.session import get_db
    from app.main import app

    def _broken_get_db():
        raise ValueError("internal secret detail that should never reach the client")
        yield  # pragma: no cover - hace de esto un generador, nunca se ejecuta

    app.dependency_overrides[get_db] = _broken_get_db
    try:
        headers = auth_headers(admin_token)
        # raise_server_exceptions=False: queremos la respuesta 500 real que arma
        # nuestro handler global, no que TestClient relance la excepción en el test.
        unsafe_client = TestClient(app, raise_server_exceptions=False)
        resp = unsafe_client.get("/api/clients", headers=headers)
    finally:
        del app.dependency_overrides[get_db]

    assert resp.status_code == 500
    assert "internal secret detail" not in resp.text
    assert resp.json() == {"detail": "Ocurrió un error interno. Si persiste, contacta al administrador."}


def test_normal_404_is_not_swallowed_by_global_handler(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.get("/api/clients/999999", headers=headers)
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Cliente no encontrado"
