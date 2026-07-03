from tests.conftest import auth_headers


def test_admin_can_create_and_list_users(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.post(
        "/api/users",
        json={"name": "Nueva Oficina", "email": "nueva.oficina@test.com", "password": "clave12345", "role": "oficina"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["role"] == "oficina"
    assert body["is_active"] is True
    assert "hashed_password" not in body
    assert "password" not in body

    list_resp = client.get("/api/users", headers=headers)
    assert list_resp.status_code == 200
    assert any(u["email"] == "nueva.oficina@test.com" for u in list_resp.json())


def test_created_user_can_log_in(client, admin_token):
    headers = auth_headers(admin_token)
    client.post(
        "/api/users",
        json={"name": "Nuevo Tecnico", "email": "nuevo.tecnico@test.com", "password": "clave12345", "role": "tecnico"},
        headers=headers,
    )
    login_resp = client.post(
        "/api/auth/login", data={"username": "nuevo.tecnico@test.com", "password": "clave12345"}
    )
    assert login_resp.status_code == 200


def test_duplicate_email_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    payload = {"name": "Duplicado", "email": "duplicado@test.com", "password": "clave12345", "role": "oficina"}
    first = client.post("/api/users", json=payload, headers=headers)
    assert first.status_code == 201
    second = client.post("/api/users", json=payload, headers=headers)
    assert second.status_code == 400


def test_non_admin_cannot_manage_users(client, oficina_token, tecnico_token):
    for token in (oficina_token, tecnico_token):
        headers = auth_headers(token)
        assert client.get("/api/users", headers=headers).status_code == 403
        assert (
            client.post(
                "/api/users",
                json={"name": "X", "email": "x@test.com", "password": "clave12345", "role": "oficina"},
                headers=headers,
            ).status_code
            == 403
        )


def test_admin_can_update_role_and_deactivate_other_user(client, admin_token):
    headers = auth_headers(admin_token)
    created = client.post(
        "/api/users",
        json={"name": "Para Editar", "email": "editar@test.com", "password": "clave12345", "role": "oficina"},
        headers=headers,
    ).json()

    resp = client.put(f"/api/users/{created['id']}", json={"role": "tecnico"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["role"] == "tecnico"

    resp = client.put(f"/api/users/{created['id']}", json={"is_active": False}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    # un usuario desactivado no puede iniciar sesión
    login_resp = client.post(
        "/api/auth/login", data={"username": "editar@test.com", "password": "clave12345"}
    )
    assert login_resp.status_code == 403


def test_admin_cannot_deactivate_or_demote_self(client, admin_token, db_session):
    from app.models.user import User

    headers = auth_headers(admin_token)
    admin_id = db_session.query(User).filter(User.email == "admin@test.com").one().id

    resp = client.put(f"/api/users/{admin_id}", json={"is_active": False}, headers=headers)
    assert resp.status_code == 400

    resp = client.put(f"/api/users/{admin_id}", json={"role": "oficina"}, headers=headers)
    assert resp.status_code == 400


def test_admin_can_reset_another_users_password(client, admin_token):
    headers = auth_headers(admin_token)
    created = client.post(
        "/api/users",
        json={"name": "Reset Pass", "email": "resetpass@test.com", "password": "clavevieja1", "role": "oficina"},
        headers=headers,
    ).json()

    resp = client.put(f"/api/users/{created['id']}", json={"password": "clavenueva1"}, headers=headers)
    assert resp.status_code == 200

    old_login = client.post(
        "/api/auth/login", data={"username": "resetpass@test.com", "password": "clavevieja1"}
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/auth/login", data={"username": "resetpass@test.com", "password": "clavenueva1"}
    )
    assert new_login.status_code == 200


def test_password_too_short_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.post(
        "/api/users",
        json={"name": "Corta", "email": "corta@test.com", "password": "123", "role": "oficina"},
        headers=headers,
    )
    assert resp.status_code == 422


def test_invalid_role_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.post(
        "/api/users",
        json={"name": "Rol Invalido", "email": "rolinvalido@test.com", "password": "clave12345", "role": "superadmin"},
        headers=headers,
    )
    assert resp.status_code == 422
