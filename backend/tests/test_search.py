from tests.conftest import auth_headers, make_project


def test_search_requires_auth(client):
    resp = client.get("/api/search", params={"q": "algo"})
    assert resp.status_code == 401


def test_search_short_query_returns_empty(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.get("/api/search", params={"q": "a"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"clients": [], "projects": [], "tickets": []}


def test_search_finds_client_project_and_ticket(client, admin_token, tecnico_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Ferretería Popular SRL")
    client.post(
        f"/api/projects/{project['id']}/tickets", json={"problem": "Cámara sin señal"}, headers=headers
    )

    by_client = client.get("/api/search", params={"q": "Ferretería"}, headers=headers).json()
    assert len(by_client["clients"]) == 1
    assert by_client["clients"][0]["name"] == "Ferretería Popular SRL"
    # buscar por cliente también trae sus proyectos
    assert any(p["id"] == project["id"] for p in by_client["projects"])

    by_project_code = client.get("/api/search", params={"q": project["code"]}, headers=headers).json()
    assert any(p["id"] == project["id"] for p in by_project_code["projects"])

    by_ticket_problem = client.get("/api/search", params={"q": "señal"}, headers=headers).json()
    assert len(by_ticket_problem["tickets"]) == 1
    assert by_ticket_problem["tickets"][0]["problem"] == "Cámara sin señal"
    assert by_ticket_problem["tickets"][0]["project_id"] == project["id"]

    # tecnico también puede buscar (acceso de lectura a clientes/proyectos/tickets)
    tecnico_resp = client.get(
        "/api/search", params={"q": project["code"]}, headers=auth_headers(tecnico_token)
    )
    assert tecnico_resp.status_code == 200


def test_search_is_case_insensitive(client, admin_token):
    headers = auth_headers(admin_token)
    make_project(client, headers, client_name="Torre Empresarial Norte")

    resp = client.get("/api/search", params={"q": "torre empresarial"}, headers=headers)
    assert len(resp.json()["clients"]) == 1
