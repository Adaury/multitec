from tests.conftest import assign_to_tecnico, auth_headers, make_project


def test_tecnico_can_view_and_create_but_not_edit_projects_and_clients(client, admin_token, tecnico_token, db_session):
    """El técnico arranca levantamientos en campo (crea cliente y proyecto), pero no edita lo existente.
    El detalle de qué campos puede tocar está en test_projects.py."""
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    assign_to_tecnico(db_session, project)
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


def test_tecnico_has_full_access_to_field_work_tabs(client, admin_token, tecnico_token, db_session):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    assign_to_tecnico(db_session, project)
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


def test_tecnico_does_not_get_the_client_portal_token(client, admin_token, tecnico_token, db_session):
    """El token del portal abre cotizaciones y facturas del cliente: ver el proyecto no debe
    darle al técnico (que no tiene acceso a dinero) esa puerta trasera."""
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)
    assign_to_tecnico(db_session, project)  # lo ve (es suyo), pero sin el enlace del portal
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=admin_headers).json()["token"]

    as_admin = client.get(f"/api/projects/{project['id']}", headers=admin_headers).json()
    assert as_admin["public_token"] == token

    as_tecnico = client.get(f"/api/projects/{project['id']}", headers=auth_headers(tecnico_token))
    assert as_tecnico.status_code == 200
    assert as_tecnico.json()["public_token"] is None
    assert token not in as_tecnico.text
