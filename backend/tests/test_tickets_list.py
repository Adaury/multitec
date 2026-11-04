from tests.conftest import assign_to_tecnico, auth_headers, make_project


def _ticket(client, headers, project_id, problem="Cámara sin imagen"):
    return client.post(f"/api/projects/{project_id}/tickets", json={"problem": problem}, headers=headers).json()


def test_lists_open_tickets_with_project_and_client(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    open_ticket = _ticket(client, headers, project["id"])
    closed = _ticket(client, headers, project["id"], "DVR apagado")
    client.put(f"/api/tickets/{closed['id']}", json={"status": "cerrado", "solution": "Reiniciado"}, headers=headers)

    rows = client.get("/api/tickets", headers=headers).json()
    assert [r["id"] for r in rows] == [open_ticket["id"]]
    assert rows[0]["project_code"] == project["code"]
    assert rows[0]["client_name"]

    every = client.get("/api/tickets", params={"open_only": False}, headers=headers).json()
    assert {r["id"] for r in every} == {open_ticket["id"], closed["id"]}


def test_technician_only_sees_tickets_of_own_projects(client, admin_token, tecnico_token, db_session):
    admin = auth_headers(admin_token)
    mine = make_project(client, admin)
    other = make_project(client, admin)
    assign_to_tecnico(db_session, mine)
    my_ticket = _ticket(client, admin, mine["id"])
    _ticket(client, admin, other["id"])

    rows = client.get("/api/tickets", headers=auth_headers(tecnico_token)).json()
    assert [r["id"] for r in rows] == [my_ticket["id"]]
