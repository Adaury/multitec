from tests.conftest import auth_headers, create_user


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def _platform_headers(client, db_session):
    create_user(db_session, "owner@test.com", "ownerpass1234", "admin", is_platform_admin=True)
    return auth_headers(_login(client, "owner@test.com", "ownerpass1234"))


def _create(client, headers, name="Seguridad Demo SRL", email="admin@demo.com"):
    return client.post(
        "/api/platform/companies",
        json={"name": name, "admin_name": "Ana Demo", "admin_email": email},
        headers=headers,
    )


def test_only_platform_admin_can_use_panel(client, admin_token):
    assert client.get("/api/platform/companies", headers=auth_headers(admin_token)).status_code == 403
    assert _create(client, auth_headers(admin_token)).status_code == 403


def test_create_company_gives_admin_with_temporary_password(client, db_session):
    headers = _platform_headers(client, db_session)
    resp = _create(client, headers)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["company"]["slug"] == "seguridad-demo-srl"
    assert body["company"]["users"] == 1

    token = _login(client, "admin@demo.com", body["temporary_password"])
    me = client.get("/api/auth/me", headers=auth_headers(token)).json()
    assert me["company_name"] == "Seguridad Demo SRL"
    assert me["must_change_password"] is True
    assert me["is_platform_admin"] is False
    changed = client.post(
        "/api/auth/change-password",
        json={"current_password": body["temporary_password"], "new_password": "NuevaClave-2026x"},
        headers=auth_headers(token),
    )
    assert changed.status_code == 200, changed.text
    # La empresa nueva no ve nada de Multitec y su admin no entra al panel de plataforma
    assert client.get("/api/clients", headers=auth_headers(token)).json() == []
    assert client.get("/api/platform/companies", headers=auth_headers(token)).status_code == 403


def test_duplicate_admin_email_rejected(client, db_session):
    headers = _platform_headers(client, db_session)
    assert _create(client, headers).status_code == 201
    assert _create(client, headers, name="Otra SRL").status_code == 400


def test_suspend_blocks_access_and_activate_restores(client, db_session):
    headers = _platform_headers(client, db_session)
    created = _create(client, headers).json()
    company_id = created["company"]["id"]
    token = _login(client, "admin@demo.com", created["temporary_password"])

    assert client.post(f"/api/platform/companies/{company_id}/suspend", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 403
    blocked = client.post("/api/auth/login", data={"username": "admin@demo.com", "password": created["temporary_password"]})
    assert blocked.status_code == 403

    assert client.post(f"/api/platform/companies/{company_id}/activate", headers=headers).status_code == 200
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 200


def test_cannot_suspend_own_company(client, db_session):
    headers = _platform_headers(client, db_session)
    assert client.post("/api/platform/companies/1/suspend", headers=headers).status_code == 400


def test_reset_admin_password(client, db_session):
    headers = _platform_headers(client, db_session)
    created = _create(client, headers).json()
    company_id = created["company"]["id"]
    resp = client.post(f"/api/platform/companies/{company_id}/reset-admin-password", headers=headers)
    assert resp.status_code == 200
    new = resp.json()["temporary_password"]
    assert new != created["temporary_password"]
    _login(client, "admin@demo.com", new)


def test_detail_lists_team(client, db_session):
    headers = _platform_headers(client, db_session)
    company_id = _create(client, headers).json()["company"]["id"]
    detail = client.get(f"/api/platform/companies/{company_id}", headers=headers).json()
    assert [u["email"] for u in detail["team"]] == ["admin@demo.com"]
