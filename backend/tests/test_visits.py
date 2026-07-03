from datetime import date, timedelta

from tests.conftest import auth_headers, create_user, make_project


def test_create_and_list_visit(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    tomorrow = (date.today() + timedelta(days=1)).isoformat()

    created = client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": tomorrow, "notes": "Instalación de cámaras"},
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "programada"
    assert body["project_code"] == project["code"]
    assert body["technician_id"] is None
    assert body["technician_name"] is None

    listed = client.get("/api/visits", headers=headers).json()
    assert len(listed) == 1
    assert listed[0]["id"] == body["id"]


def test_visit_can_be_assigned_a_technician(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    technician = create_user(db_session, "tec-visit@test.com", "tecpass123", "tecnico")
    project = make_project(client, headers)

    created = client.post(
        "/api/visits",
        json={
            "project_id": project["id"],
            "technician_id": technician.id,
            "scheduled_date": date.today().isoformat(),
            "scheduled_time": "09:30:00",
        },
        headers=headers,
    ).json()
    assert created["technician_id"] == technician.id
    assert created["technician_name"] == "tec-visit"
    assert created["scheduled_time"] == "09:30:00"


def test_filter_visits_by_date_range(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    today = date.today()

    client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": today.isoformat()},
        headers=headers,
    )
    client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": (today + timedelta(days=10)).isoformat()},
        headers=headers,
    )

    resp = client.get(
        "/api/visits",
        params={"start": today.isoformat(), "end": (today + timedelta(days=2)).isoformat()},
        headers=headers,
    )
    assert len(resp.json()) == 1


def test_update_visit_status_and_reschedule(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    visit = client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": date.today().isoformat()},
        headers=headers,
    ).json()

    new_date = (date.today() + timedelta(days=3)).isoformat()
    updated = client.put(
        f"/api/visits/{visit['id']}",
        json={"scheduled_date": new_date, "status": "completada"},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["scheduled_date"] == new_date
    assert updated.json()["status"] == "completada"


def test_update_visit_rejects_invalid_status(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    visit = client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": date.today().isoformat()},
        headers=headers,
    ).json()

    resp = client.put(f"/api/visits/{visit['id']}", json={"status": "no_existe"}, headers=headers)
    assert resp.status_code == 400


def test_tecnico_can_create_and_view_visits(client, tecnico_token, admin_token):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)

    tecnico_headers = auth_headers(tecnico_token)
    created = client.post(
        "/api/visits",
        json={"project_id": project["id"], "scheduled_date": date.today().isoformat()},
        headers=tecnico_headers,
    )
    assert created.status_code == 201

    listed = client.get("/api/visits", headers=tecnico_headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_create_visit_for_missing_project_fails(client, admin_token):
    resp = client.post(
        "/api/visits",
        json={"project_id": 999999, "scheduled_date": date.today().isoformat()},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
