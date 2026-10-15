from tests.conftest import auth_headers, make_project


def test_tecnico_can_view_and_create_but_not_edit_projects_and_clients(client, admin_token, tecnico_token):
    """El técnico arranca levantamientos en campo (crea cliente y proyecto), pero no edita lo existente.
    El detalle de qué campos puede tocar está en test_projects.py."""
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    tecnico_headers = auth_headers(tecnico_token)

    assert client.get("/api/projects", headers=tecnico_headers).status_code == 200
    assert client.get(f"/api/projects/{project['id']}", headers=tecnico_headers).status_code == 200
    assert client.get("/api/clients", headers=tecnico_headers).status_code == 200

    created_client = client.post("/api/clients", json={"name": "Cliente de campo"}, headers=tecnico_headers)
    assert created_client.status_code == 201
    created_project = client.post(
        "/api/projects", json={"client_id": created_client.json()["id"]}, headers=tecnico_headers
    )
    assert created_project.status_code == 201

    # Editar sigue siendo de oficina/admin.
    assert (
        client.put(
            f"/api/clients/{created_client.json()['id']}", json={"name": "Otro"}, headers=tecnico_headers
        ).status_code
        == 403
    )
    assert (
        client.put(
            f"/api/projects/{created_project.json()['id']}", json={"status": "cerrado"}, headers=tecnico_headers
        ).status_code
        == 403
    )


def test_tecnico_has_full_access_to_field_work_tabs(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    tecnico_headers = auth_headers(tecnico_token)
    project_id = project["id"]

    assert client.get(f"/api/projects/{project_id}/survey", headers=tecnico_headers).status_code == 200
    assert (
        client.put(
            f"/api/projects/{project_id}/survey",
            json={"notes": "actualizado por tecnico"},
            headers=tecnico_headers,
        ).status_code
        == 200
    )
    assert client.get(f"/api/projects/{project_id}/engineering", headers=tecnico_headers).status_code == 200
    assert client.get(f"/api/projects/{project_id}/execution", headers=tecnico_headers).status_code == 200
    assert (
        client.post(f"/api/projects/{project_id}/execution/advance", headers=tecnico_headers).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/projects/{project_id}/logbook",
            json={"comment": "Visita de instalación"},
            headers=tecnico_headers,
        ).status_code
        == 201
    )
    assert (
        client.post(
            f"/api/projects/{project_id}/tickets",
            json={"problem": "Cliente reporta falla"},
            headers=tecnico_headers,
        ).status_code
        == 201
    )


def test_tecnico_denied_from_commercial_and_financial_endpoints(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    tecnico_headers = auth_headers(tecnico_token)
    project_id = project["id"]

    assert client.get(f"/api/projects/{project_id}/budgets", headers=tecnico_headers).status_code == 403
    assert client.get(f"/api/projects/{project_id}/quotes", headers=tecnico_headers).status_code == 403
    assert client.get(f"/api/projects/{project_id}/materials", headers=tecnico_headers).status_code == 403
    assert client.get(f"/api/projects/{project_id}/pre-invoices", headers=tecnico_headers).status_code == 403
    assert client.get(f"/api/projects/{project_id}/extensions", headers=tecnico_headers).status_code == 403
    assert client.get("/api/catalog", headers=tecnico_headers).status_code == 403
