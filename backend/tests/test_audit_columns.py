from tests.conftest import auth_headers, make_project


def test_client_and_project_record_created_by(client, admin_token, db_session):
    from app.models.user import User

    headers = auth_headers(admin_token)
    admin_id = db_session.query(User).filter(User.email == "admin@test.com").one().id

    project = make_project(client, headers)

    client_resp = client.get("/api/clients", headers=headers).json()
    our_client = next(c for c in client_resp if c["id"] == project["client_id"])
    assert our_client["created_by"] == admin_id
    assert our_client["created_at"] is not None

    assert project["created_by"] == admin_id
    assert project["created_at"] is not None


def test_budget_quote_and_material_record_created_by(client, admin_token, db_session):
    from app.models.user import User

    headers = auth_headers(admin_token)
    admin_id = db_session.query(User).filter(User.email == "admin@test.com").one().id
    project = make_project(client, headers)

    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()
    assert budget["created_by"] == admin_id

    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    assert quote["created_by"] == admin_id

    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    materials = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()
    assert materials[0]["created_by"] == admin_id


def test_ticket_records_created_by(client, admin_token, tecnico_token, db_session):
    from app.models.user import User

    admin_headers = auth_headers(admin_token)
    tecnico_headers = auth_headers(tecnico_token)
    tecnico_id = db_session.query(User).filter(User.email == "tecnico@test.com").one().id

    project = make_project(client, admin_headers)
    ticket = client.post(
        f"/api/projects/{project['id']}/tickets",
        json={"problem": "Cámara desconectada"},
        headers=tecnico_headers,
    ).json()
    assert ticket["created_by"] == tecnico_id
