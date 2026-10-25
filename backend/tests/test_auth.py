from tests.conftest import auth_headers, create_user


def test_login_success_and_me(client, admin_token):
    resp = client.get("/api/auth/me", headers=auth_headers(admin_token))
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"
    assert resp.json()["email"] == "admin@test.com"


def test_login_wrong_password(client, db_session):
    create_user(db_session, "user@test.com", "correctpass123", "oficina")
    resp = client.post("/api/auth/login", data={"username": "user@test.com", "password": "wrongpass"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    resp = client.post("/api/auth/login", data={"username": "nadie@test.com", "password": "x"})
    assert resp.status_code == 401


def test_protected_route_requires_token(client):
    resp = client.get("/api/clients")
    assert resp.status_code == 401


def test_protected_route_rejects_garbage_token(client):
    resp = client.get("/api/clients", headers=auth_headers("not-a-real-token"))
    assert resp.status_code == 401


def test_account_locks_after_repeated_failures_even_from_another_ip_and_unlocks_on_success_path(client, db_session):
    from app.core import lockout
    from tests.conftest import create_user

    create_user(db_session, "lock@test.com", "lockpass1234", "oficina")
    for _ in range(5):
        resp = client.post("/api/auth/login", data={"username": "lock@test.com", "password": "mala-clave"})
        assert resp.status_code == 401

    # El 6.º intento ya no llega a comprobar la clave, ni siquiera la correcta.
    blocked = client.post("/api/auth/login", data={"username": "lock@test.com", "password": "lockpass1234"})
    assert blocked.status_code == 429
    assert int(blocked.headers["retry-after"]) > 0

    lockout.reset()  # simula que pasó la espera
    ok = client.post("/api/auth/login", data={"username": "lock@test.com", "password": "lockpass1234"})
    assert ok.status_code == 200


def test_lockout_applies_to_unknown_emails_too_so_it_does_not_reveal_accounts(client):
    for _ in range(5):
        client.post("/api/auth/login", data={"username": "fantasma@test.com", "password": "x"})
    resp = client.post("/api/auth/login", data={"username": "fantasma@test.com", "password": "x"})
    assert resp.status_code == 429  # igual que una cuenta que sí existe


def test_a_successful_login_clears_the_failure_count(client, db_session):
    from tests.conftest import create_user

    create_user(db_session, "reset@test.com", "resetpass1234", "oficina")
    for _ in range(4):
        client.post("/api/auth/login", data={"username": "reset@test.com", "password": "mala"})
    assert client.post("/api/auth/login", data={"username": "reset@test.com", "password": "resetpass1234"}).status_code == 200
    for _ in range(4):  # 4 más: si no se hubiera borrado el conteo, ya estaría bloqueada
        assert client.post("/api/auth/login", data={"username": "reset@test.com", "password": "mala"}).status_code == 401
