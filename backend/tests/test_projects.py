from tests.conftest import auth_headers, make_project


def test_create_project_generates_code_and_stubs(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    assert project["code"] == "PRY-000001"
    assert project["status"] == "levantamiento"

    detail_resp = client.get(f"/api/projects/{project['id']}", headers=headers)
    assert detail_resp.status_code == 200
    assert detail_resp.json()["client"]["name"] == "Cliente de prueba"

    # el proyecto nace con levantamiento e ingeniería vacíos, y 5 etapas de ejecución
    survey_resp = client.get(f"/api/projects/{project['id']}/survey", headers=headers)
    assert survey_resp.status_code == 200

    engineering_resp = client.get(f"/api/projects/{project['id']}/engineering", headers=headers)
    assert engineering_resp.status_code == 200

    execution_resp = client.get(f"/api/projects/{project['id']}/execution", headers=headers)
    assert execution_resp.status_code == 200
    assert len(execution_resp.json()["stages"]) == 5
    assert execution_resp.json()["progress_percent"] == 0


def test_project_codes_increment_across_projects(client, admin_token):
    headers = auth_headers(admin_token)
    first = make_project(client, headers, client_name="Cliente Uno")
    second = make_project(client, headers, client_name="Cliente Dos")
    assert first["code"] == "PRY-000001"
    assert second["code"] == "PRY-000002"


def test_update_project_status(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    resp = client.put(f"/api/projects/{project['id']}", json={"status": "ingenieria"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "ingenieria"


def test_create_project_for_missing_client_fails(client, admin_token):
    resp = client.post("/api/projects", json={"client_id": 999999}, headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_create_project_with_missing_responsible_fails(client, admin_token):
    headers = auth_headers(admin_token)
    client_resp = client.post("/api/clients", json={"name": "Cliente de prueba"}, headers=headers)
    resp = client.post(
        "/api/projects",
        json={"client_id": client_resp.json()["id"], "responsible_id": 999999},
        headers=headers,
    )
    assert resp.status_code == 404


def test_update_project_with_missing_responsible_fails(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    resp = client.put(f"/api/projects/{project['id']}", json={"responsible_id": 999999}, headers=headers)
    assert resp.status_code == 404


def test_project_location_roundtrip(client, admin_token):
    headers = auth_headers(admin_token)
    client_id = client.post("/api/clients", json={"name": "Cliente obras"}, headers=headers).json()["id"]
    created = client.post(
        "/api/projects",
        json={
            "client_id": client_id,
            "address": "Obra norte, km 12",
            "location_url": "https://www.google.com/maps?q=18.5,-69.9",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["address"] == "Obra norte, km 12"
    assert body["location_url"] == "https://www.google.com/maps?q=18.5,-69.9"

    updated = client.put(
        f"/api/projects/{body['id']}", json={"address": "Obra sur", "location_url": None}, headers=headers
    )
    assert updated.status_code == 200
    assert updated.json()["address"] == "Obra sur"
    assert updated.json()["location_url"] is None

    detail = client.get(f"/api/projects/{body['id']}", headers=headers).json()
    assert detail["address"] == "Obra sur"


def test_project_location_defaults_to_empty(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    assert project["address"] is None
    assert project["location_url"] is None
