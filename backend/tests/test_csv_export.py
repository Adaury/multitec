from tests.conftest import auth_headers, make_project, seed_ncf_sequence

BOM = "﻿"


def _approved_budget_items(client, headers, project):
    return client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()


def test_export_clients_csv(client, admin_token):
    headers = auth_headers(admin_token)
    client.post("/api/clients", json={"name": "Ferretería Ñuñez"}, headers=headers)

    resp = client.get("/api/clients/export", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "clientes.csv" in resp.headers["content-disposition"]
    text = resp.content.decode("utf-8")
    assert text.startswith(BOM)
    assert "Ferretería Ñuñez" in text


def test_export_clients_forbidden_for_tecnico(client, tecnico_token):
    resp = client.get("/api/clients/export", headers=auth_headers(tecnico_token))
    assert resp.status_code == 403


def test_export_projects_csv(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Torre Norte")

    resp = client.get("/api/projects/export", headers=headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8")
    assert project["code"] in text
    assert "Torre Norte" in text


def test_export_invoices_csv_includes_ncf(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    budget = _approved_budget_items(client, headers, project)
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    resp = client.get("/api/invoices/export", headers=headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8")
    assert invoice["code"] in text
    assert invoice["ncf"] in text


def test_export_dashboard_csv(client, admin_token):
    headers = auth_headers(admin_token)
    make_project(client, headers)

    resp = client.get("/api/reports/dashboard/export", headers=headers)
    assert resp.status_code == 200
    text = resp.content.decode("utf-8")
    assert "Proyectos por estado" in text
    assert "levantamiento" in text


def test_export_dashboard_forbidden_for_tecnico(client, tecnico_token):
    resp = client.get("/api/reports/dashboard/export", headers=auth_headers(tecnico_token))
    assert resp.status_code == 403
