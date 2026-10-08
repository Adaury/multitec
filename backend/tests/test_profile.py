from tests.conftest import auth_headers, create_user


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_any_role_can_update_own_name(client, tecnico_token):
    resp = client.put("/api/auth/me", json={"name": "  Nuevo Nombre "}, headers=auth_headers(tecnico_token))
    assert resp.status_code == 200
    assert resp.json()["name"] == "Nuevo Nombre"
    assert client.get("/api/auth/me", headers=auth_headers(tecnico_token)).json()["name"] == "Nuevo Nombre"


def test_update_name_rejects_blank(client, oficina_token):
    resp = client.put("/api/auth/me", json={"name": "   "}, headers=auth_headers(oficina_token))
    assert resp.status_code == 422


def test_change_password_success_and_new_login_works(client, db_session):
    create_user(db_session, "cp@test.com", "oldpassword1", "oficina")
    tokens = _login(client, "cp@test.com", "oldpassword1")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpassword1", "new_password": "newpassword2"},
        headers=auth_headers(tokens["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["access_token"] and resp.json()["refresh_token"]
    assert client.post("/api/auth/login", data={"username": "cp@test.com", "password": "oldpassword1"}).status_code == 401
    _login(client, "cp@test.com", "newpassword2")


def test_change_password_wrong_current(client, oficina_token):
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "wrong-password", "new_password": "newpassword2"},
        headers=auth_headers(oficina_token),
    )
    assert resp.status_code == 400


def test_change_password_rejects_same_short_and_long(client, oficina_token):
    h = auth_headers(oficina_token)
    same = client.post(
        "/api/auth/change-password",
        json={"current_password": "oficinapass123", "new_password": "oficinapass123"},
        headers=h,
    )
    assert same.status_code == 400
    short = client.post(
        "/api/auth/change-password", json={"current_password": "oficinapass123", "new_password": "short"}, headers=h
    )
    assert short.status_code == 422
    long = client.post(
        "/api/auth/change-password",
        json={"current_password": "oficinapass123", "new_password": "x" * 73},
        headers=h,
    )
    assert long.status_code == 422


def test_change_password_requires_auth(client):
    resp = client.post("/api/auth/change-password", json={"current_password": "a", "new_password": "b" * 8})
    assert resp.status_code == 401


def test_change_password_revokes_other_sessions(client, db_session):
    create_user(db_session, "cp2@test.com", "oldpassword1", "oficina")
    device_a = _login(client, "cp2@test.com", "oldpassword1")
    device_b = _login(client, "cp2@test.com", "oldpassword1")
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "oldpassword1", "new_password": "newpassword2"},
        headers=auth_headers(device_a["access_token"]),
    )
    new_tokens = resp.json()
    # Primero la sesión nueva: reusar el token revocado de device_b dispara la detección de
    # robo (revoca todas las sesiones del usuario), así que va al final.
    assert client.post("/api/auth/refresh", json={"refresh_token": new_tokens["refresh_token"]}).status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": device_b["refresh_token"]}).status_code == 401


def test_admin_password_reset_revokes_user_sessions(client, db_session, admin_token):
    user = create_user(db_session, "victim@test.com", "oldpassword1", "oficina")
    tokens = _login(client, "victim@test.com", "oldpassword1")
    resp = client.put(f"/api/users/{user.id}", json={"password": "resetpass123"}, headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401


def test_deactivating_user_revokes_sessions(client, db_session, admin_token):
    user = create_user(db_session, "gone@test.com", "oldpassword1", "oficina")
    tokens = _login(client, "gone@test.com", "oldpassword1")
    resp = client.put(f"/api/users/{user.id}", json={"is_active": False}, headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert client.post("/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}).status_code == 401
