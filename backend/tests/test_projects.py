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


def test_technician_can_start_a_field_survey_but_not_edit_the_rest(client, admin_token, tecnico_token):
    """El levantamiento rápido en campo lo hace el técnico: crea el cliente y el proyecto y guarda la
    ubicación de la obra. Lo demás (estado, responsable, datos del cliente) sigue siendo de oficina."""
    admin_headers = auth_headers(admin_token)
    tech_headers = auth_headers(tecnico_token)

    created_client = client.post("/api/clients", json={"name": "Cliente de campo"}, headers=tech_headers)
    assert created_client.status_code == 201, created_client.text
    created_project = client.post(
        "/api/projects",
        json={"client_id": created_client.json()["id"], "survey_type": "Cámaras"},
        headers=tech_headers,
    )
    assert created_project.status_code == 201, created_project.text
    project_id = created_project.json()["id"]

    # Ubicación y tipo de levantamiento: sí.
    located = client.put(
        f"/api/projects/{project_id}",
        json={"address": "Calle 1", "location_url": "https://maps.example/x"},
        headers=tech_headers,
    )
    assert located.status_code == 200, located.text

    # Estado, responsable o descripción: no.
    for forbidden in ({"status": "cerrado"}, {"responsible_id": 1}, {"description": "otra"}):
        resp = client.put(f"/api/projects/{project_id}", json=forbidden, headers=tech_headers)
        assert resp.status_code == 403, forbidden
    assert (
        client.put(
            f"/api/clients/{created_client.json()['id']}", json={"name": "Otro nombre"}, headers=tech_headers
        ).status_code
        == 403
    )

    # Oficina/admin conservan todo.
    assert client.put(f"/api/projects/{project_id}", json={"status": "cerrado"}, headers=admin_headers).status_code == 200
