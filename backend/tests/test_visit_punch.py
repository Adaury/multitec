"""Entrada y salida del técnico en cada visita, validación del técnico asignado y hoja de tiempo."""

from tests.conftest import assign_to_tecnico, auth_headers, create_user, make_project


def _visit(client, headers, project, technician_id=None, day="2026-11-12"):
    resp = client.post(
        "/api/visits",
        json={"project_id": project["id"], "technician_id": technician_id, "scheduled_date": day, "duration_min": 90},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _tecnico_id(client, token):
    return client.get("/api/auth/me", headers=auth_headers(token)).json()["id"]


def test_technician_checks_in_and_out_and_the_visit_closes(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    assign_to_tecnico(db_session, project)
    tec_id = _tecnico_id(client, tecnico_token)
    visit = _visit(client, admin, project, tec_id)
    assert visit["status"] == "programada" and visit["duration_min"] == 90 and visit["checkin_at"] is None

    tec = auth_headers(tecnico_token)
    arrived = client.post(f"/api/visits/{visit['id']}/checkin", json={"lat": 18.4861, "lng": -69.9312}, headers=tec)
    assert arrived.status_code == 200, arrived.text
    body = arrived.json()
    assert body["status"] == "en_sitio" and body["checkin_at"] and body["checkin_lat"] == 18.4861
    assert body["minutes_on_site"] is None  # aún no sale

    # No se puede marcar entrada dos veces ni salir antes de entrar.
    assert client.post(f"/api/visits/{visit['id']}/checkin", headers=tec).status_code == 400

    left = client.post(f"/api/visits/{visit['id']}/checkout", json={"lat": 18.4862, "lng": -69.9313}, headers=tec)
    assert left.status_code == 200, left.text
    assert left.json()["status"] == "completada" and left.json()["checkout_at"]
    assert left.json()["minutes_on_site"] is not None
    assert client.post(f"/api/visits/{visit['id']}/checkout", headers=tec).status_code == 400


def test_checkout_requires_checkin_first_and_gps_is_optional(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    assign_to_tecnico(db_session, project)
    tec_id = _tecnico_id(client, tecnico_token)
    visit = _visit(client, admin, project, tec_id)
    tec = auth_headers(tecnico_token)

    assert client.post(f"/api/visits/{visit['id']}/checkout", headers=tec).status_code == 400
    sin_gps = client.post(f"/api/visits/{visit['id']}/checkin", headers=tec)  # sin cuerpo: no dio permiso de ubicación
    assert sin_gps.status_code == 200
    assert sin_gps.json()["checkin_lat"] is None and sin_gps.json()["checkin_at"]


def test_only_the_assigned_technician_can_punch_and_bad_coordinates_are_rejected(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    assign_to_tecnico(db_session, project)
    other = create_user(db_session, "otrotec@test.com", "otrotecnico123", "tecnico")
    visit = _visit(client, admin, project, other.id)

    assert client.post(f"/api/visits/{visit['id']}/checkin", headers=auth_headers(tecnico_token)).status_code == 403

    mine = _visit(client, admin, project, _tecnico_id(client, tecnico_token))
    bad = client.post(f"/api/visits/{mine['id']}/checkin", json={"lat": 400, "lng": 0}, headers=auth_headers(tecnico_token))
    assert bad.status_code == 422


def test_an_unassigned_visit_goes_to_whoever_arrives(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    assign_to_tecnico(db_session, project)
    visit = _visit(client, admin, project, None)
    arrived = client.post(f"/api/visits/{visit['id']}/checkin", headers=auth_headers(tecnico_token))
    assert arrived.status_code == 200
    assert arrived.json()["technician_id"] == _tecnico_id(client, tecnico_token)


def test_visits_cannot_be_assigned_to_a_deactivated_user(client, admin_token, db_session):
    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    gone = create_user(db_session, "baja@test.com", "claveparabaja12", "tecnico")
    client.put(f"/api/users/{gone.id}", json={"is_active": False}, headers=admin)

    resp = client.post(
        "/api/visits",
        json={"project_id": project["id"], "technician_id": gone.id, "scheduled_date": "2026-11-12"},
        headers=admin,
    )
    assert resp.status_code == 400 and "desactivado" in resp.json()["detail"]

    ok = _visit(client, admin, project, None)
    again = client.put(f"/api/visits/{ok['id']}", json={"technician_id": gone.id}, headers=admin)
    assert again.status_code == 400


def test_timesheet_sums_hours_per_technician_and_exports_csv(client, admin_token, tecnico_token, db_session):
    from datetime import datetime, timedelta, timezone

    from app.models.visit import Visit

    admin = auth_headers(admin_token)
    project = make_project(client, admin)
    assign_to_tecnico(db_session, project)
    tec_id = _tecnico_id(client, tecnico_token)
    for hours in (2, 1.5):
        visit = _visit(client, admin, project, tec_id)
        row = db_session.get(Visit, visit["id"])
        row.status = "completada"
        row.checkin_at = datetime(2026, 11, 12, 14, 0, tzinfo=timezone.utc)
        row.checkout_at = row.checkin_at + timedelta(hours=hours)
        db_session.commit()
    pending = _visit(client, admin, project, tec_id)  # sin entrada: no aparece
    open_visit = _visit(client, admin, project, tec_id)
    row = db_session.get(Visit, open_visit["id"])
    row.status = "en_sitio"
    row.checkin_at = datetime(2026, 11, 12, 20, 0, tzinfo=timezone.utc)
    db_session.commit()
    assert pending["status"] == "programada"

    params = {"start": "2026-11-12", "end": "2026-11-12"}
    report = client.get("/api/reports/timesheet", params=params, headers=admin).json()
    assert len(report["rows"]) == 3
    total = report["totals"][0]
    assert total["visits"] == 3 and total["minutes"] == 210 and total["open"] == 1

    csv_text = client.get("/api/reports/timesheet/export", params=params, headers=admin).content.decode("utf-8")
    assert "Entrada" in csv_text and "2.0" in csv_text and "1.5" in csv_text

    assert client.get("/api/reports/timesheet", headers=auth_headers(tecnico_token)).status_code == 403
    assert client.get("/api/reports/timesheet", params={"start": "2026-11-12", "end": "2026-01-01"}, headers=admin).status_code == 400
