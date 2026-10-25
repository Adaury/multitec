"""Administración del equipo: ficha del técnico, último acceso, restablecer contraseña, sesiones y auditoría."""

from tests.conftest import auth_headers, create_user


def _login(client, email, password):
    return client.post("/api/auth/login", data={"username": email, "password": password})


def test_admin_fills_the_team_profile_and_sees_last_login(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    created = client.post(
        "/api/users",
        json={
            "name": "Luis Técnico",
            "email": "luis@test.com",
            "password": "Tornillo-azul-47",
            "role": "tecnico",
            "phone": "809-555-0100",
            "zone": "Moca y Cibao",
            "skills": "CCTV, redes",
            "vehicle": "Hilux P-1234",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert (body["phone"], body["zone"], body["skills"], body["vehicle"]) == (
        "809-555-0100",
        "Moca y Cibao",
        "CCTV, redes",
        "Hilux P-1234",
    )
    assert body["last_login_at"] is None

    edited = client.put(f"/api/users/{body['id']}", json={"zone": "Santiago"}, headers=headers)
    assert edited.json()["zone"] == "Santiago" and edited.json()["skills"] == "CCTV, redes"

    assert _login(client, "luis@test.com", "Tornillo-azul-47").status_code == 200
    listed = {u["email"]: u for u in client.get("/api/users", headers=headers).json()}
    assert listed["luis@test.com"]["last_login_at"] is not None


def test_reset_password_gives_a_one_time_temporary_password_and_closes_sessions(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    user = create_user(db_session, "olvido@test.com", "claveviejaXY1", "oficina")
    old = _login(client, "olvido@test.com", "claveviejaXY1").json()

    reset = client.post(f"/api/users/{user.id}/reset-password", headers=headers)
    assert reset.status_code == 200
    temporary = reset.json()["temporary_password"]
    assert len(temporary) >= 10

    # La sesión anterior ya no sirve, la clave vieja tampoco, y la temporal obliga a cambiarla.
    assert client.post("/api/auth/refresh", json={"refresh_token": old["refresh_token"]}).status_code == 401
    assert _login(client, "olvido@test.com", "claveviejaXY1").status_code == 401
    new = _login(client, "olvido@test.com", temporary)
    assert new.status_code == 200
    me = client.get("/api/auth/me", headers=auth_headers(new.json()["access_token"]))
    assert me.json()["must_change_password"] is True


def test_reset_password_is_admin_only_and_not_for_yourself(client, admin_token, oficina_token, db_session):
    target = create_user(db_session, "otro@test.com", "otraclave1234X", "tecnico")
    assert client.post(f"/api/users/{target.id}/reset-password", headers=auth_headers(oficina_token)).status_code == 403
    me = client.get("/api/auth/me", headers=auth_headers(admin_token)).json()
    assert client.post(f"/api/users/{me['id']}/reset-password", headers=auth_headers(admin_token)).status_code == 400


def test_sessions_can_be_listed_and_closed_by_admin_and_by_the_owner(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    user = create_user(db_session, "dosdisp@test.com", "dispositivos123", "tecnico")
    phone = _login(client, "dosdisp@test.com", "dispositivos123").json()
    client.cookies.clear()
    laptop = _login(client, "dosdisp@test.com", "dispositivos123").json()

    sessions = client.get(f"/api/users/{user.id}/sessions", headers=headers).json()
    assert len(sessions) == 2
    assert all(s["ip"] and s["last_used_at"] for s in sessions)

    assert client.delete(f"/api/users/{user.id}/sessions/{sessions[-1]['id']}", headers=headers).status_code == 204
    assert len(client.get(f"/api/users/{user.id}/sessions", headers=headers).json()) == 1

    # El propio usuario ve sus sesiones y puede cerrarlas todas.
    own = client.get("/api/auth/sessions", headers=auth_headers(laptop["access_token"]))
    assert own.status_code == 200 and len(own.json()) == 1
    assert client.post("/api/auth/logout-all", headers=auth_headers(laptop["access_token"])).status_code == 204
    assert client.post("/api/auth/refresh", json={"refresh_token": laptop["refresh_token"]}).status_code == 401
    assert client.post("/api/auth/refresh", json={"refresh_token": phone["refresh_token"]}).status_code == 401


def test_audit_log_records_logins_and_user_changes_without_secrets(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    client.post("/api/auth/login", data={"username": "admin@test.com", "password": "mala-clave-xx"})
    created = client.post(
        "/api/users",
        json={"name": "Nuevo", "email": "nuevo@test.com", "password": "Tornillo-azul-47", "role": "oficina"},
        headers=headers,
    ).json()
    client.put(f"/api/users/{created['id']}", json={"role": "tecnico", "password": "OtraClave-nueva-9"}, headers=headers)

    rows = client.get("/api/audit", headers=headers).json()
    actions = [r["action"] for r in rows]
    assert {"login", "login_failed", "user_created", "user_updated"} <= set(actions)
    failed = next(r for r in rows if r["action"] == "login_failed")
    assert failed["user_email"] == "admin@test.com" and failed["user_id"] is None and failed["ip"]

    # Ni las claves ni nada parecido llegan a la bitácora.
    everything = str(rows)
    assert "Tornillo-azul-47" not in everything and "OtraClave-nueva-9" not in everything
    updated = next(r for r in rows if r["action"] == "user_updated")
    assert "tecnico" in updated["detail"] and "cambiada" in updated["detail"]

    only_logins = client.get("/api/audit", params={"action": "login"}, headers=headers).json()
    assert only_logins and {r["action"] for r in only_logins} == {"login"}


def test_audit_log_is_admin_only(client, oficina_token, tecnico_token):
    assert client.get("/api/audit", headers=auth_headers(oficina_token)).status_code == 403
    assert client.get("/api/audit", headers=auth_headers(tecnico_token)).status_code == 403
    assert client.get("/api/audit").status_code == 401


def test_workload_counts_visits_tickets_and_hours(client, admin_token, tecnico_token, db_session):
    from datetime import datetime, timedelta, timezone

    from app.models.user import User
    from app.models.visit import Visit
    from tests.conftest import make_project

    headers = auth_headers(admin_token)
    tec = db_session.query(User).filter(User.email == "tecnico@test.com").one()
    project = make_project(client, headers)
    day = "2026-11-10"
    for status_, hours in [("programada", None), ("completada", 2)]:
        visit = client.post(
            "/api/visits", json={"project_id": project["id"], "technician_id": tec.id, "scheduled_date": day}, headers=headers
        ).json()
        row = db_session.get(Visit, visit["id"])
        row.status = status_
        if hours:
            row.checkin_at = datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc)
            row.checkout_at = row.checkin_at + timedelta(hours=hours)
        db_session.commit()
    client.post(f"/api/projects/{project['id']}/tickets", json={"problem": "No graba", "technician_id": tec.id}, headers=headers)

    one = client.get(f"/api/users/{tec.id}/workload", params={"start": day, "end": day}, headers=headers).json()
    assert (one["visits_total"], one["visits_pending"], one["visits_done"]) == (2, 1, 1)
    assert one["open_tickets"] == 1 and one["hours_on_site"] == 2.0

    team = client.get("/api/users/workload", params={"start": day, "end": day}, headers=headers).json()
    assert any(row["user_id"] == tec.id and row["visits_total"] == 2 for row in team)
    assert client.get("/api/users/workload", headers=auth_headers(tecnico_token)).status_code == 403


def test_sensitive_actions_leave_an_audit_trail(client, admin_token, db_session):
    from tests.conftest import make_category, make_project

    headers = auth_headers(admin_token)
    category = make_category(client, headers)
    product = client.post(
        "/api/catalog", json={"category_id": category["id"], "name": "Cámara IP", "price": 100}, headers=headers
    ).json()
    client.put(f"/api/catalog/{product['id']}", json={"price": 150}, headers=headers)
    client.put("/api/catalog/bulk-prices", json={"items": [{"id": product["id"], "price": 175}]}, headers=headers)

    project = make_project(client, headers)
    client.post(f"/api/projects/{project['id']}/public-link", headers=headers)
    client.post(f"/api/projects/{project['id']}/public-link", headers=headers)  # rota
    client.delete(f"/api/projects/{project['id']}/public-link", headers=headers)

    client.put("/api/company", json={"name": "Multitec SRL", "rnc": "131234567"}, headers=headers)
    seq = client.post(
        "/api/ncf-sequences",
        json={"ncf_type": "B02", "description": "Consumo", "range_start": 1, "range_end": 50, "expires_at": "2027-12-31"},
        headers=headers,
    )
    assert seq.status_code == 201, seq.text

    rows = client.get("/api/audit", params={"limit": 200}, headers=headers).json()
    actions = {r["action"] for r in rows}
    assert {
        "product_price_changed",
        "catalog_prices_changed",
        "portal_link_created",
        "portal_link_rotated",
        "portal_link_revoked",
        "company_updated",
        "ncf_sequence_created",
    } <= actions
    price = next(r for r in rows if r["action"] == "product_price_changed")
    assert "100" in price["detail"] and "150" in price["detail"]
    company = next(r for r in rows if r["action"] == "company_updated")
    assert "rnc" in company["detail"] and "131234567" not in company["detail"]  # el campo, no el valor
