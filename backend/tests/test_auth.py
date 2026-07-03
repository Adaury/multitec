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
