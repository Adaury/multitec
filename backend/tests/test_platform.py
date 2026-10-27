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


# ---------------------------------------------------------------- periodo de prueba, tope de usuarios y demo


def _change_temp(client, email, temporary):
    token = _login(client, email, temporary)
    resp = client.post(
        "/api/auth/change-password",
        json={"current_password": temporary, "new_password": "NuevaClave-2026x"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_trial_expiry_blocks_the_company_and_extending_restores_it(client, db_session):
    from datetime import datetime, timedelta, timezone

    from app.db.tenant import tenant_bypass
    from app.models.company import Company

    headers = _platform_headers(client, db_session)
    resp = client.post(
        "/api/platform/companies",
        json={"name": "Prueba SRL", "admin_name": "Ana", "admin_email": "ana@prueba.com", "trial_days": 7},
        headers=headers,
    )
    created = resp.json()
    assert created["company"]["state"] == "prueba"
    assert 5 <= created["company"]["days_left"] <= 7
    company_id = created["company"]["id"]
    token = _change_temp(client, "ana@prueba.com", created["temporary_password"])
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 200

    with tenant_bypass(db_session):  # la prueba venció ayer
        db_session.get(Company, company_id).trial_ends_at = datetime.now(timezone.utc) - timedelta(days=1)
        db_session.commit()
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 403
    blocked = client.post("/api/auth/login", data={"username": "ana@prueba.com", "password": "NuevaClave-2026x"})
    assert blocked.status_code == 403
    assert "periodo de prueba" in blocked.json()["detail"]
    listed = {c["id"]: c for c in client.get("/api/platform/companies", headers=headers).json()}
    assert listed[company_id]["state"] == "vencida"

    extended = client.put(f"/api/platform/companies/{company_id}", json={"extend_days": 30}, headers=headers).json()
    assert extended["state"] == "prueba" and extended["days_left"] >= 28
    assert client.get("/api/auth/me", headers=auth_headers(token)).status_code == 200

    cleared = client.put(f"/api/platform/companies/{company_id}", json={"clear_trial": True}, headers=headers).json()
    assert cleared["state"] == "activa" and cleared["trial_ends_at"] is None


def test_user_limit_blocks_creating_and_reactivating_beyond_the_plan(client, db_session):
    headers = _platform_headers(client, db_session)
    created = client.post(
        "/api/platform/companies",
        json={"name": "Chica SRL", "admin_name": "Eva", "admin_email": "eva@chica.com", "max_users": 2},
        headers=headers,
    ).json()
    token = _change_temp(client, "eva@chica.com", created["temporary_password"])
    h = auth_headers(token)
    body = {"name": "Tec Uno", "email": "uno@chica.com", "password": "clave-larga-123", "role": "tecnico"}
    first = client.post("/api/users", json=body, headers=h)
    assert first.status_code == 201, first.text
    over = client.post("/api/users", json={**body, "name": "Tec Dos", "email": "dos@chica.com"}, headers=h)
    assert over.status_code == 400 and "hasta 2 usuarios" in over.json()["detail"]
    # Desactivar a uno libera el cupo; reactivarlo con el cupo lleno no se puede
    uno = first.json()["id"]
    assert client.put(f"/api/users/{uno}", json={"is_active": False}, headers=h).status_code == 200
    assert client.post("/api/users", json={**body, "name": "Tec Dos", "email": "dos@chica.com"}, headers=h).status_code == 201
    assert client.put(f"/api/users/{uno}", json={"is_active": True}, headers=h).status_code == 400


def test_demo_company_has_technicians_sample_data_and_expires(client, db_session):
    headers = _platform_headers(client, db_session)
    resp = client.post("/api/platform/demos", json={"technicians": 3, "days": 14}, headers=headers)
    assert resp.status_code == 201, resp.text
    demo = resp.json()
    assert demo["company"]["is_demo"] is True and demo["company"]["state"] == "prueba"
    assert demo["company"]["max_users"] == 4
    roles = sorted(a["role"] for a in demo["accounts"])
    assert roles == ["admin", "tecnico", "tecnico", "tecnico"]

    tech = next(a for a in demo["accounts"] if a["role"] == "tecnico")
    admin = next(a for a in demo["accounts"] if a["role"] == "admin")
    admin_token = _change_temp(client, admin["email"], admin["temporary_password"])
    tech_token = _change_temp(client, tech["email"], tech["temporary_password"])
    # El admin demo ve los 3 proyectos de ejemplo; cada técnico solo el suyo; y nada de Multitec
    assert len(client.get("/api/projects", headers=auth_headers(admin_token)).json()) == 3
    assert len(client.get("/api/projects", headers=auth_headers(tech_token)).json()) == 1
    assert all("(ejemplo)" in c["name"] for c in client.get("/api/clients", headers=auth_headers(admin_token)).json())
    me = client.get("/api/auth/me", headers=auth_headers(tech_token)).json()
    assert me["company_name"].startswith("Multitec Demo")


def test_platform_can_set_any_user_password_by_hand_or_random(client, db_session):
    headers = _platform_headers(client, db_session)
    demo = client.post("/api/platform/demos", json={"technicians": 2, "days": 7}, headers=headers).json()
    company_id = demo["company"]["id"]
    tech = next(a for a in demo["accounts"] if a["role"] == "tecnico")
    detail = client.get(f"/api/platform/companies/{company_id}", headers=headers).json()
    tech_id = next(u["id"] for u in detail["team"] if u["email"] == tech["email"])
    url = f"/api/platform/companies/{company_id}/users/{tech_id}/password"

    manual = client.post(url, json={"password": "Mi-Clave-Demo-77"}, headers=headers)
    assert manual.status_code == 200 and manual.json()["temporary_password"] == "Mi-Clave-Demo-77"
    _login(client, tech["email"], "Mi-Clave-Demo-77")  # la vieja ya no sirve, la nueva sí
    old = client.post("/api/auth/login", data={"username": tech["email"], "password": tech["temporary_password"]})
    assert old.status_code == 401

    random_one = client.post(url, json={}, headers=headers).json()["temporary_password"]
    assert len(random_one) >= 10
    _login(client, tech["email"], random_one)

    assert client.post(url, json={"password": "corta"}, headers=headers).status_code == 422  # política de claves
    assert client.post(f"/api/platform/companies/{company_id}/users/999999/password", json={}, headers=headers).status_code == 404
    # no se puede tocar una cuenta de otra empresa pasando el id de empresa equivocado
    assert client.post(f"/api/platform/companies/1/users/{tech_id}/password", json={}, headers=headers).status_code == 404
