from tests.conftest import auth_headers, create_user


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def _new_user(client, admin_token, email="nuevo@test.com", password="temporal-123"):
    resp = client.post(
        "/api/users",
        json={"name": "Usuario Nuevo", "email": email, "password": password, "role": "oficina"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_user_created_by_admin_must_change_the_temporary_password(client, admin_token):
    _new_user(client, admin_token)
    token = _login(client, "nuevo@test.com", "temporal-123")["access_token"]
    headers = auth_headers(token)

    # Entra y se ve a sí mismo, con la marca...
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200 and me.json()["must_change_password"] is True

    # ...pero nada más funciona hasta que cambie la contraseña (lo hace cumplir el servidor).
    for path in ("/api/clients", "/api/projects", "/api/catalog"):
        blocked = client.get(path, headers=headers)
        assert blocked.status_code == 403, path
        assert "cambiar tu contraseña" in blocked.json()["detail"]

    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": "temporal-123", "new_password": "mi-clave-nueva-9"},
        headers=headers,
    )
    assert changed.status_code == 200, changed.text

    fresh = auth_headers(changed.json()["access_token"])
    assert client.get("/api/auth/me", headers=fresh).json()["must_change_password"] is False
    assert client.get("/api/clients", headers=fresh).status_code == 200


def test_admin_reset_marks_the_password_as_temporary_but_own_change_does_not(client, admin_token, db_session):
    target = _new_user(client, admin_token, email="reset@test.com")
    first = _login(client, "reset@test.com", "temporal-123")["access_token"]
    client.post(
        "/api/auth/change-password",
        json={"current_password": "temporal-123", "new_password": "ya-la-cambie-1"},
        headers=auth_headers(first),
    )
    ok = _login(client, "reset@test.com", "ya-la-cambie-1")["access_token"]
    assert client.get("/api/clients", headers=auth_headers(ok)).status_code == 200

    # El admin la restablece: vuelve a ser temporal.
    resp = client.put(
        f"/api/users/{target['id']}", json={"password": "otra-temporal-2"}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    token = _login(client, "reset@test.com", "otra-temporal-2")["access_token"]
    assert client.get("/api/clients", headers=auth_headers(token)).status_code == 403

    # Un admin que se pone SU propia contraseña desde la gestión de usuarios no queda marcado.
    admins = [u for u in client.get("/api/users", headers=auth_headers(admin_token)).json() if u["role"] == "admin"]
    own_id = admins[0]["id"]
    client.put(f"/api/users/{own_id}", json={"password": "mi-propia-clave-7"}, headers=auth_headers(admin_token))
    own = client.get("/api/auth/me", headers=auth_headers(admin_token)).json()
    assert own["must_change_password"] is False


def test_existing_users_and_helpers_are_not_affected(client, db_session):
    create_user(db_session, "viejo@test.com", "una-clave-larga-1", "oficina")
    token = _login(client, "viejo@test.com", "una-clave-larga-1")["access_token"]
    assert client.get("/api/auth/me", headers=auth_headers(token)).json()["must_change_password"] is False
    assert client.get("/api/clients", headers=auth_headers(token)).status_code == 200


def test_logout_and_refresh_still_work_while_the_password_is_temporary(client, admin_token):
    _new_user(client, admin_token, email="sesion@test.com")
    tokens = _login(client, "sesion@test.com", "temporal-123")
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text
    out = client.post(
        "/api/auth/logout",
        json={"refresh_token": refreshed.json()["refresh_token"]},
        headers=auth_headers(refreshed.json()["access_token"]),
    )
    assert out.status_code in (200, 204), out.text
