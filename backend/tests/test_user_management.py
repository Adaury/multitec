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


def test_password_over_bcrypt_limit_rejected(client, admin_token):
    """bcrypt no acepta más de 72 bytes — antes de este fix, hash_password() truena con
    un 500 sin manejar en vez de un 422 de validación limpio."""
    headers = auth_headers(admin_token)
    resp = client.post(
        "/api/users",
        json={
            "name": "Clave Larga",
            "email": "clavelarga@test.com",
            "password": "a" * 73,
            "role": "oficina",
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_login_with_oversized_password_is_rejected_not_500(client, admin_token):
    resp = client.post("/api/auth/login", data={"username": "admin@test.com", "password": "a" * 100})
    assert resp.status_code == 401


def test_email_is_normalized_to_lowercase_and_duplicates_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    first = client.post(
        "/api/users",
        json={"name": "Mayus", "email": "MAYUS@Test.com", "password": "clave12345", "role": "oficina"},
        headers=headers,
    )
    assert first.status_code == 201, first.text
    assert first.json()["email"] == "mayus@test.com"

    # el mismo correo con otra combinación de mayúsculas se rechaza como duplicado
    second = client.post(
        "/api/users",
        json={"name": "Otro", "email": "mayus@TEST.COM", "password": "clave12345", "role": "oficina"},
        headers=headers,
    )
    assert second.status_code == 400


def test_login_is_case_insensitive_on_email(client, admin_token):
    headers = auth_headers(admin_token)
    client.post(
        "/api/users",
        json={"name": "Case Test", "email": "casetest@test.com", "password": "clave12345", "role": "oficina"},
        headers=headers,
    )
    resp = client.post("/api/auth/login", data={"username": "CaseTest@Test.com", "password": "clave12345"})
    assert resp.status_code == 200


def _make_user(client, headers, name, email):
    resp = client.post(
        "/api/users",
        json={"name": name, "email": email, "password": "clave12345", "role": "tecnico"},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_admin_can_change_a_users_email_and_the_user_logs_in_with_the_new_one(client, admin_token):
    headers = auth_headers(admin_token)
    user = _make_user(client, headers, "Juan Tecnico", "juan.tecnico@test.com")

    resp = client.put(
        f"/api/users/{user['id']}",
        json={"name": "Frank Santos", "email": "Frank.Santos@Test.com"},
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Frank Santos"
    assert resp.json()["email"] == "frank.santos@test.com"  # normalizado a minúsculas

    new_login = client.post("/api/auth/login", data={"username": "frank.santos@test.com", "password": "clave12345"})
    assert new_login.status_code == 200
    old_login = client.post("/api/auth/login", data={"username": "juan.tecnico@test.com", "password": "clave12345"})
    assert old_login.status_code == 401


def test_changing_email_to_one_already_in_use_is_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    _make_user(client, headers, "Primero", "primero@test.com")
    second = _make_user(client, headers, "Segundo", "segundo@test.com")

    resp = client.put(f"/api/users/{second['id']}", json={"email": "Primero@test.com"}, headers=headers)

    assert resp.status_code == 400
    assert "Ya existe un usuario con ese correo" in resp.json()["detail"]
    # El usuario conserva su correo anterior.
    users = {u["id"]: u["email"] for u in client.get("/api/users", headers=headers).json()}
    assert users[second["id"]] == "segundo@test.com"


def test_empty_email_does_not_erase_the_users_email(client, admin_token):
    headers = auth_headers(admin_token)
    user = _make_user(client, headers, "Sin cambios", "sin.cambios@test.com")

    resp = client.put(f"/api/users/{user['id']}", json={"name": "Nuevo Nombre", "email": None}, headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "sin.cambios@test.com"


def test_invalid_email_is_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    user = _make_user(client, headers, "Correo malo", "correo.malo@test.com")

    resp = client.put(f"/api/users/{user['id']}", json={"email": "esto-no-es-un-correo"}, headers=headers)

    assert resp.status_code == 422


def test_new_passwords_must_be_long_enough_and_not_common(client, admin_token):
    from tests.conftest import auth_headers

    headers = auth_headers(admin_token)
    for bad in ["corta123", "1234567890", "contraseña123", "aaaaaaaaaaaa", "Multitec2026"]:
        resp = client.post(
            "/api/users", json={"name": "X", "email": "x@test.com", "password": bad, "role": "oficina"}, headers=headers
        )
        assert resp.status_code == 422, f"{bad} debió rechazarse"

    ok = client.post(
        "/api/users",
        json={"name": "X", "email": "x@test.com", "password": "Tornillo-azul-47", "role": "oficina"},
        headers=headers,
    )
    assert ok.status_code == 201, ok.text


def test_changing_password_applies_the_same_policy(client, admin_token):
    from tests.conftest import auth_headers

    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": "adminpass123", "new_password": "12345678"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
