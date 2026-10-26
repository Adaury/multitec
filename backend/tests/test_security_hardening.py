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


def test_uploaded_file_extension_comes_from_validated_type_not_filename(client, admin_token):
    """Un 'x.html' declarado como image/png no debe guardarse como .html: /uploads lo serviría como
    página web en el mismo origen que la app (XSS almacenado)."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    files = {"file": ("evil.html", io.BytesIO(PNG_HEADER + b"<script>alert(1)</script>"), "image/png")}
    resp = client.post(
        f"/api/projects/{project['id']}/survey/assets",
        data={"kind": "photo"},
        files=files,
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["file_path"].endswith(".png")
    assert ".html" not in resp.json()["file_path"]


def test_a_file_that_is_not_the_declared_image_is_rejected(client, admin_token):
    """Un HTML, un PDF o un ejecutable declarado "image/png" ya no se guarda: los primeros bytes mandan."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    url = f"/api/projects/{project['id']}/survey/assets"

    for body, declared in [
        (b"<script>alert(1)</script>", "image/png"),
        (b"%PDF-1.7 ...", "image/jpeg"),
        (PNG_HEADER + b"0" * 30, "image/jpeg"),  # un PNG real declarado como JPEG
        (b"MZ\x90\x00 programa", "image/webp"),
    ]:
        resp = client.post(
            url, data={"kind": "photo"}, files={"file": ("x", io.BytesIO(body), declared)}, headers=headers
        )
        assert resp.status_code == 400, f"{declared} con {body[:6]!r} debió rechazarse"

    jpeg = b"\xff\xd8\xff\xe0" + b"0" * 30
    ok = client.post(url, data={"kind": "photo"}, files={"file": ("x", io.BytesIO(jpeg), "image/jpeg")}, headers=headers)
    assert ok.status_code == 201, ok.text


def test_an_audio_note_that_is_really_a_web_page_or_program_is_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    resp = client.post(
        f"/api/projects/{project['id']}/survey/assets",
        data={"kind": "audio"},
        files={"file": ("nota.webm", io.BytesIO(b"<html>no soy audio</html>"), "audio/webm")},
        headers=headers,
    )
    assert resp.status_code == 400


def test_oversized_upload_is_cut_off_while_reading(client, admin_token, monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.get_settings(), "max_upload_mb", 1)
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    big = PNG_HEADER + b"0" * (2 * 1024 * 1024)
    resp = client.post(
        f"/api/projects/{project['id']}/survey/assets",
        data={"kind": "photo"},
        files={"file": ("grande.png", io.BytesIO(big), "image/png")},
        headers=headers,
    )
    assert resp.status_code == 413


PNG_HEADER = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A])


def _upload_survey_photo(client, headers) -> str:
    project = make_project(client, headers)
    files = {"file": ("foto.png", io.BytesIO(PNG_HEADER + b"0" * 50), "image/png")}
    created = client.post(
        f"/api/projects/{project['id']}/survey/assets", data={"kind": "photo"}, files=files, headers=headers
    ).json()
    parts = created["file_path"].split("/")
    return "/".join(parts[parts.index("c1"):])  # c<empresa>/surveys/<id>/<archivo>


def test_uploads_require_a_session_and_are_served_with_nosniff(client, admin_token):
    headers = auth_headers(admin_token)
    relative = _upload_survey_photo(client, headers)

    assert client.get(f"/uploads/{relative}").status_code == 401

    resp = client.get(f"/uploads/{relative}", headers=headers)
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"


def test_uploads_reject_path_traversal(client, admin_token):
    headers = auth_headers(admin_token)
    _upload_survey_photo(client, headers)

    for attempt in ("../multitec.db", "..%2f..%2fmultitec.db", "surveys/../../app/main.py"):
        resp = client.get(f"/uploads/{attempt}", headers=headers)
        assert resp.status_code == 404, attempt


def test_api_docs_are_off_by_default(client):
    """/docs, /redoc y /openapi.json listan todas las rutas: no deben estar a la vista salvo que se active."""
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404, path
