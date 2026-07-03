from datetime import date

from tests.conftest import auth_headers, make_project, seed_ncf_sequence


def _approved_quote(client, headers, project):
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    return quote


def test_dashboard_summary_forbidden_for_tecnico(client, tecnico_token):
    resp = client.get("/api/reports/dashboard", headers=auth_headers(tecnico_token))
    assert resp.status_code == 403


def test_dashboard_summary_counts_projects_by_status(client, admin_token):
    headers = auth_headers(admin_token)
    make_project(client, headers, client_name="Cliente A")
    make_project(client, headers, client_name="Cliente B")

    resp = client.get("/api/reports/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    by_status = {row["status"]: row["count"] for row in data["projects_by_status"]}
    assert by_status.get("levantamiento") == 2


def test_dashboard_summary_includes_current_month_invoicing(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    quote = _approved_quote(client, headers, project)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    resp = client.get("/api/reports/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["monthly_invoicing"]) == 6
    current_month = date.today().strftime("%Y-%m")
    current_row = next(row for row in data["monthly_invoicing"] if row["month"] == current_month)
    assert current_row["total"] == invoice["total"]


def test_dashboard_summary_counts_pending_quotes_and_open_tickets(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Router", "quantity": 1, "unit_price": 50}]},
        headers=headers,
    )
    budget = client.get(f"/api/projects/{project['id']}/budgets", headers=headers).json()[0]
    client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)

    client.post(f"/api/projects/{project['id']}/tickets", json={"problem": "No enciende"}, headers=headers)

    resp = client.get("/api/reports/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["quotes_pending"] == 1
    assert data["open_tickets_total"] == 1
    assert data["open_tickets_by_technician"][0]["technician"] == "Sin asignar"
