from tests.conftest import create_user


def test_login_returns_both_tokens(client, db_session):
    create_user(db_session, "refresh@test.com", "refreshpass123", "oficina")
    resp = client.post("/api/auth/login", data={"username": "refresh@test.com", "password": "refreshpass123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["access_token"]
    assert body["refresh_token"]


def test_refresh_issues_new_access_token(client, db_session):
    create_user(db_session, "refresh2@test.com", "refreshpass123", "oficina")
    login_resp = client.post(
        "/api/auth/login", data={"username": "refresh2@test.com", "password": "refreshpass123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    refresh_resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 200
    new_access_token = refresh_resp.json()["access_token"]
    assert new_access_token

    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {new_access_token}"})
    assert me_resp.status_code == 200
    assert me_resp.json()["email"] == "refresh2@test.com"


def test_refresh_with_invalid_token_fails(client):
    resp = client.post("/api/auth/refresh", json={"refresh_token": "not-a-real-token"})
    assert resp.status_code == 401


def test_logout_revokes_refresh_token(client, db_session):
    create_user(db_session, "refresh3@test.com", "refreshpass123", "oficina")
    login_resp = client.post(
        "/api/auth/login", data={"username": "refresh3@test.com", "password": "refreshpass123"}
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = client.post("/api/auth/logout", json={"refresh_token": refresh_token})
    assert logout_resp.status_code == 204

    # el mismo refresh token ya no debe servir para pedir un nuevo access token
    refresh_resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_resp.status_code == 401
