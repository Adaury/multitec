from datetime import date, timedelta

from tests.conftest import auth_headers, create_user, make_project


def _login(client, email, password):
    resp = client.post("/api/auth/login", data={"username": email, "password": password})
    assert resp.status_code == 200, resp.text
    return auth_headers(resp.json()["access_token"])


def _tecnico(client, db_session, email="tec-hoy@test.com"):
    user = create_user(db_session, email, "tecpass12345", "tecnico")
    return user, _login(client, email, "tecpass12345")


def test_requires_authentication(client):
    assert client.get("/api/assistant/today").status_code in (401, 403)


def test_empty_day_is_a_valid_answer(client, admin_token):
    body = client.get("/api/assistant/today", headers=auth_headers(admin_token)).json()

    assert body["visits"] == [] and body["ready_to_quote"] == []
    assert body["quotes_waiting"] == [] and body["tickets"] == []
    assert body["today"] == date.today().isoformat()


def test_technician_sees_only_todays_visits_assigned_to_them(client, admin_token, db_session):
    admin = auth_headers(admin_token)
    technician, tec_headers = _tecnico(client, db_session)
    other = create_user(db_session, "otro-tec@test.com", "tecpass12345", "tecnico")
    project = make_project(client, admin, client_name="Cliente de la visita")
    today = date.today().isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    for tech_id, day, time in [(technician.id, today, "09:30:00"), (other.id, today, "10:00:00"), (technician.id, tomorrow, "08:00:00")]:
        client.post(
            "/api/visits",
            json={"project_id": project["id"], "technician_id": tech_id, "scheduled_date": day, "scheduled_time": time},
            headers=admin,
        )

    mine = client.get("/api/assistant/today", headers=tec_headers).json()
    everyone = client.get("/api/assistant/today", headers=admin).json()

    assert [v["scheduled_time"] for v in mine["visits"]] == ["09:30:00"]
    assert mine["visits"][0]["client_name"] == "Cliente de la visita"
    assert len(everyone["visits"]) == 2  # admin ve las dos de hoy


def test_survey_with_notes_and_no_quote_is_ready_to_quote(client, admin_token):
    headers = auth_headers(admin_token)
    ready = make_project(client, headers, client_name="Listo para cotizar")
    empty = make_project(client, headers, client_name="Sin notas")
    quoted = make_project(client, headers, client_name="Ya cotizado")
    client.put(f"/api/projects/{ready['id']}/survey", json={"notes": "8 cámaras IP y un NVR"}, headers=headers)
    client.put(f"/api/projects/{quoted['id']}/survey", json={"notes": "4 cámaras"}, headers=headers)
    budget = client.post(
        f"/api/projects/{quoted['id']}/budgets",
        json={"items": [{"description": "Cámara", "quantity": 4, "unit_price": 100}]},
        headers=headers,
    ).json()
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)

    body = client.get("/api/assistant/today", headers=headers).json()

    names = [p["client_name"] for p in body["ready_to_quote"]]
    assert names == ["Listo para cotizar"]
    assert empty["id"] not in [p["project_id"] for p in body["ready_to_quote"]]
    assert [q["client_name"] for q in body["quotes_waiting"]] == ["Ya cotizado"]
    assert body["quotes_waiting"][0]["days_pending"] == 0


def test_technician_only_sees_their_own_projects(client, admin_token, db_session):
    admin = auth_headers(admin_token)
    technician, tec_headers = _tecnico(client, db_session, "tec-proyectos@test.com")
    mine = make_project(client, admin, client_name="Mío")
    other = make_project(client, admin, client_name="Ajeno")
    client.put(f"/api/projects/{mine['id']}", json={"responsible_id": technician.id}, headers=admin)
    for project in (mine, other):
        client.put(f"/api/projects/{project['id']}/survey", json={"notes": "Algo que cotizar"}, headers=admin)

    body = client.get("/api/assistant/today", headers=tec_headers).json()

    assert [p["client_name"] for p in body["ready_to_quote"]] == ["Mío"]


def test_open_tickets_assigned_to_the_user_show_up(client, admin_token, db_session):
    admin = auth_headers(admin_token)
    technician, tec_headers = _tecnico(client, db_session, "tec-tickets@test.com")
    project = make_project(client, admin, client_name="Con ticket")
    client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "Cámara 3 sin imagen", "technician_id": technician.id},
        headers=admin,
    )

    body = client.get("/api/assistant/today", headers=tec_headers).json()

    assert [t["problem"] for t in body["tickets"]] == ["Cámara 3 sin imagen"]
    # Admin y oficina ven todos los tickets abiertos, no solo los suyos.
    assert len(client.get("/api/assistant/today", headers=admin).json()["tickets"]) == 1


def test_recent_open_projects_are_offered_to_continue(client, admin_token):
    headers = auth_headers(admin_token)
    for name in ["Primero", "Segundo", "Tercero", "Cuarto"]:
        make_project(client, headers, client_name=name)
    closed = make_project(client, headers, client_name="Cerrado")
    client.put(f"/api/projects/{closed['id']}", json={"status": "cerrado"}, headers=headers)

    body = client.get("/api/assistant/today", headers=headers).json()

    names = [p["client_name"] for p in body["continue_projects"]]
    assert len(names) == 3
    assert "Cerrado" not in names
    assert body["continue_projects"][0]["status"] == "levantamiento"
