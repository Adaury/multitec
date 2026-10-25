"""Un técnico ve solo lo suyo: lo que creó, donde es responsable o donde tiene una visita o ticket
asignado (y los clientes de esos proyectos). Admin y oficina ven todo. Ver services/access.py."""

from tests.conftest import auth_headers, create_user, make_project


def _tecnico(client, db_session, email):
    create_user(db_session, email, "tecnicopass123", "tecnico")
    token = client.post("/api/auth/login", data={"username": email, "password": "tecnicopass123"}).json()["access_token"]
    headers = auth_headers(token)
    return headers, client.get("/api/auth/me", headers=headers).json()["id"]


def _ids(resp):
    assert resp.status_code == 200, resp.text
    return {row["id"] for row in resp.json()}


def test_tecnico_does_not_see_a_project_that_is_not_theirs(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    project = make_project(client, admin, client_name="Cliente ajeno")
    tec, _ = _tecnico(client, db_session, "tec1@test.com")

    assert project["id"] not in _ids(client.get("/api/projects", headers=tec))
    assert client.get(f"/api/clients/{project['client_id']}", headers=tec).status_code == 404
    assert project["client_id"] not in _ids(client.get("/api/clients", headers=tec))
    # Todo lo anidado en el proyecto responde igual que si no existiera.
    pid = project["id"]
    for method, url in [
        ("get", f"/api/projects/{pid}"),
        ("get", f"/api/projects/{pid}/survey"),
        ("get", f"/api/projects/{pid}/engineering"),
        ("get", f"/api/projects/{pid}/execution"),
        ("get", f"/api/projects/{pid}/logbook"),
        ("get", f"/api/projects/{pid}/tickets"),
        ("put", f"/api/projects/{pid}"),
    ]:
        resp = getattr(client, method)(url, headers=tec, **({"json": {"address": "x"}} if method == "put" else {}))
        assert resp.status_code == 404, f"{method} {url} -> {resp.status_code}"
    assert client.post(f"/api/projects/{pid}/logbook", json={"comment": "x"}, headers=tec).status_code == 404

    # El admin sigue viéndolo todo.
    assert pid in _ids(client.get("/api/projects", headers=admin))
    assert client.get(f"/api/projects/{pid}", headers=admin).status_code == 200


def test_tecnico_sees_what_they_created(client, db_session):
    tec, _ = _tecnico(client, db_session, "tec2@test.com")
    project = make_project(client, tec, client_name="Cliente de campo")
    assert project["id"] in _ids(client.get("/api/projects", headers=tec))
    assert project["client_id"] in _ids(client.get("/api/clients", headers=tec))
    assert client.get(f"/api/projects/{project['id']}/survey", headers=tec).status_code == 200


def test_tecnico_sees_a_project_where_they_are_responsible(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    tec, tec_id = _tecnico(client, db_session, "tec3@test.com")
    project = make_project(client, admin)
    assert client.get(f"/api/projects/{project['id']}", headers=tec).status_code == 404

    client.put(f"/api/projects/{project['id']}", json={"responsible_id": tec_id}, headers=admin)
    assert client.get(f"/api/projects/{project['id']}", headers=tec).status_code == 200
    assert project["client_id"] in _ids(client.get("/api/clients", headers=tec))  # y su cliente


def test_tecnico_sees_a_project_where_they_have_a_visit_or_ticket(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    tec, tec_id = _tecnico(client, db_session, "tec4@test.com")
    by_visit = make_project(client, admin, client_name="Por visita")
    by_ticket = make_project(client, admin, client_name="Por ticket")
    other = make_project(client, admin, client_name="Otro")

    visit = client.post(
        "/api/visits",
        json={"project_id": by_visit["id"], "technician_id": tec_id, "scheduled_date": "2026-11-02"},
        headers=admin,
    )
    assert visit.status_code == 201, visit.text
    ticket = client.post(
        f"/api/projects/{by_ticket['id']}/tickets", json={"problem": "No graba", "technician_id": tec_id}, headers=admin
    )
    assert ticket.status_code == 201, ticket.text

    visible = _ids(client.get("/api/projects", headers=tec))
    assert {by_visit["id"], by_ticket["id"]} <= visible
    assert other["id"] not in visible

    # El ticket asignado se puede actualizar; uno de un proyecto ajeno no.
    assert client.put(f"/api/tickets/{ticket.json()['id']}", json={"status": "en_proceso"}, headers=tec).status_code == 200
    foreign = client.post(f"/api/projects/{other['id']}/tickets", json={"problem": "Otro"}, headers=admin).json()
    assert client.put(f"/api/tickets/{foreign['id']}", json={"status": "en_proceso"}, headers=tec).status_code == 404
    assert client.get(f"/api/tickets/{foreign['id']}/history", headers=tec).status_code == 404


def test_tecnico_cannot_use_logbook_photos_or_visits_of_other_projects(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    tec, _ = _tecnico(client, db_session, "tec5@test.com")
    project = make_project(client, admin)
    entry = client.post(f"/api/projects/{project['id']}/logbook", json={"comment": "avance"}, headers=admin).json()
    assert client.post(f"/api/logbook/{entry['id']}/photos", headers=tec).status_code == 404

    visit = client.post(
        "/api/visits", json={"project_id": project["id"], "scheduled_date": "2026-11-03"}, headers=admin
    ).json()
    assert visit["id"] not in _ids(client.get("/api/visits", headers=tec))
    assert client.put(f"/api/visits/{visit['id']}", json={"notes": "x"}, headers=tec).status_code == 404
    assert (
        client.post("/api/visits", json={"project_id": project["id"], "scheduled_date": "2026-11-04"}, headers=tec).status_code
        == 404
    )
    assert visit["id"] in _ids(client.get("/api/visits", headers=admin))


def test_tecnico_search_and_project_creation_are_scoped(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    tec, _ = _tecnico(client, db_session, "tec6@test.com")
    theirs = make_project(client, tec, client_name="Zafiro Propio")
    ajeno = make_project(client, admin, client_name="Zafiro Ajeno")

    found = client.get("/api/search", params={"q": "Zafiro"}, headers=tec).json()
    assert [c["name"] for c in found["clients"]] == ["Zafiro Propio"]
    assert [p["id"] for p in found["projects"]] == [theirs["id"]]
    assert {c["name"] for c in client.get("/api/search", params={"q": "Zafiro"}, headers=admin).json()["clients"]} == {
        "Zafiro Propio",
        "Zafiro Ajeno",
    }

    # No puede colgar un proyecto de un cliente que no ve.
    resp = client.post("/api/projects", json={"client_id": ajeno["client_id"]}, headers=tec)
    assert resp.status_code == 404


def test_tecnico_ai_ask_about_a_foreign_project_is_denied(client, db_session, admin_token):
    admin = auth_headers(admin_token)
    tec, _ = _tecnico(client, db_session, "tec7@test.com")
    project = make_project(client, admin)
    resp = client.post("/api/ai/ask", json={"question": "¿cómo va?", "project_id": project["id"]}, headers=tec)
    assert resp.status_code == 404


def test_oficina_still_sees_everything(client, db_session, admin_token, oficina_token):
    project = make_project(client, auth_headers(admin_token))
    oficina = auth_headers(oficina_token)
    assert project["id"] in _ids(client.get("/api/projects", headers=oficina))
    assert project["client_id"] in _ids(client.get("/api/clients", headers=oficina))
