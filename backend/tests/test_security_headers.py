def test_api_responses_are_not_cacheable_and_carry_basic_headers(client, admin_token):
    from tests.conftest import auth_headers

    resp = client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["referrer-policy"] == "no-referrer"


def test_health_has_nosniff_but_uploads_keep_their_own_cache_policy(client, admin_token):
    from tests.conftest import auth_headers

    assert client.get("/api/health").headers["x-content-type-options"] == "nosniff"
    # /uploads trae su propia política (private, max-age): el middleware no la pisa. Un archivo que
    # no existe responde 404, así que se comprueba con una ruta real más abajo en test_uploads.
    assert "no-store" not in client.get("/uploads/no-existe.png", headers=auth_headers(admin_token)).headers.get(
        "cache-control", ""
    )


def test_cors_only_allows_listed_methods_and_headers(client):
    resp = client.options(
        "/api/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "x-evil-header",
        },
    )
    assert "x-evil-header" not in resp.headers.get("access-control-allow-headers", "").lower()
