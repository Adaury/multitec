from tests.conftest import auth_headers, create_user, make_project


def _approved_budget_items(client, headers, project):
    return client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Router", "quantity": 1, "unit_price": 50}]},
        headers=headers,
    ).json()


def test_quote_pending_creates_in_app_notification_for_admin(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    budget = _approved_budget_items(client, headers, project)
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)

    notifications = client.get("/api/notifications", headers=headers).json()
    assert len(notifications) == 1
    assert "pendiente de aprobar" in notifications[0]["title"]
    assert notifications[0]["read"] is False
    assert notifications[0]["link"] == f"/proyectos/{project['id']}?tab=cotizacion"


def test_ticket_assignment_creates_in_app_notification_for_technician(client, admin_token, db_session):
    admin_headers = auth_headers(admin_token)
    technician = create_user(db_session, "assignee@test.com", "tecpass123", "tecnico")
    project = make_project(client, admin_headers)

    client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "No enciende", "technician_id": technician.id},
        headers=admin_headers,
    )

    login = client.post(
        "/api/auth/login", data={"username": "assignee@test.com", "password": "tecpass123"}
    ).json()
    tech_headers = auth_headers(login["access_token"])

    notifications = client.get("/api/notifications", headers=tech_headers).json()
    assert len(notifications) == 1
    assert "asignado" in notifications[0]["title"]
    assert notifications[0]["link"] == f"/proyectos/{project['id']}?tab=tickets"

    # el admin no debe ver la notificación del técnico
    admin_notifications = client.get("/api/notifications", headers=admin_headers).json()
    assert admin_notifications == []


def test_unread_count_and_mark_read(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    budget = _approved_budget_items(client, headers, project)
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)

    unread = client.get("/api/notifications/unread-count", headers=headers).json()
    assert unread["count"] == 1

    notification = client.get("/api/notifications", headers=headers).json()[0]
    marked = client.put(f"/api/notifications/{notification['id']}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["read"] is True

    unread_after = client.get("/api/notifications/unread-count", headers=headers).json()
    assert unread_after["count"] == 0


def test_mark_all_read(client, admin_token):
    headers = auth_headers(admin_token)
    for i in range(3):
        project = make_project(client, headers, client_name=f"Cliente {i}")
        budget = _approved_budget_items(client, headers, project)
        client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)

    assert client.get("/api/notifications/unread-count", headers=headers).json()["count"] == 3
    client.post("/api/notifications/read-all", headers=headers)
    assert client.get("/api/notifications/unread-count", headers=headers).json()["count"] == 0


def test_cannot_mark_other_users_notification_as_read(client, admin_token, db_session):
    admin_headers = auth_headers(admin_token)
    technician = create_user(db_session, "other-tech@test.com", "tecpass123", "tecnico")
    project = make_project(client, admin_headers)
    client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "Fallo cámara", "technician_id": technician.id},
        headers=admin_headers,
    )

    login = client.post(
        "/api/auth/login", data={"username": "other-tech@test.com", "password": "tecpass123"}
    ).json()
    tech_notification = client.get(
        "/api/notifications", headers=auth_headers(login["access_token"])
    ).json()[0]

    resp = client.put(f"/api/notifications/{tech_notification['id']}/read", headers=admin_headers)
    assert resp.status_code == 404
