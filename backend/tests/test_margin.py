from tests.conftest import auth_headers, make_category, make_project, seed_ncf_sequence


def _make_product(client, headers, price=100, cost=60):
    category = make_category(client, headers)
    resp = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cámara IP", "unit": "unidad", "price": price, "cost": cost},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _quote_with_mixed_items(client, headers, project, product):
    """Una línea con producto de catálogo (costo conocido) + una de mano de obra sin
    producto (costo desconocido), para probar que el margen distingue ambas."""
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={
            "items": [
                {"product_id": product["id"], "quantity": 2, "description": "", "unit_price": 0},
                {"description": "Mano de obra", "quantity": 1, "unit_price": 50},
            ]
        },
        headers=headers,
    ).json()
    return client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()


def test_quote_margin_computes_cost_and_flags_uncosted_lines(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _make_product(client, headers, price=100, cost=60)
    quote = _quote_with_mixed_items(client, headers, project, product)

    resp = client.get(f"/api/quotes/{quote['id']}/margin", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["revenue"] == 250  # 2*100 + 50
    assert data["cost"] == 120  # 2*60; la línea de mano de obra no aporta costo
    assert data["margin"] == 130
    assert data["margin_pct"] == 0.52
    assert data["lines_total"] == 2
    assert data["lines_costed"] == 1
    assert data["basis"] == "cotizado"


def test_quote_margin_forbidden_for_non_admin(client, oficina_token, tecnico_token):
    for token in (oficina_token, tecnico_token):
        resp = client.get("/api/quotes/1/margin", headers=auth_headers(token))
        assert resp.status_code == 403


def test_invoice_margin_matches_quote_lines(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    product = _make_product(client, headers, price=100, cost=60)
    quote = _quote_with_mixed_items(client, headers, project, product)
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    resp = client.get(f"/api/invoices/{invoice['id']}/margin", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["revenue"] == 250
    assert data["cost"] == 120
    assert data["basis"] == "facturado"


def test_invoice_margin_forbidden_for_non_admin(client, oficina_token, tecnico_token):
    for token in (oficina_token, tecnico_token):
        resp = client.get("/api/invoices/1/margin", headers=auth_headers(token))
        assert resp.status_code == 403


def test_project_margin_basis_transitions(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)

    resp = client.get(f"/api/projects/{project['id']}/margin", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["basis"] == "ninguno"

    product = _make_product(client, headers, price=100, cost=60)
    quote = _quote_with_mixed_items(client, headers, project, product)
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)

    resp = client.get(f"/api/projects/{project['id']}/margin", headers=headers)
    data = resp.json()
    assert data["basis"] == "cotizado"
    assert data["revenue"] == 250

    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)

    resp = client.get(f"/api/projects/{project['id']}/margin", headers=headers)
    data = resp.json()
    assert data["basis"] == "facturado"
    assert data["revenue"] == 250


def test_project_margin_forbidden_for_non_admin(client, oficina_token, tecnico_token):
    for token in (oficina_token, tecnico_token):
        resp = client.get("/api/projects/1/margin", headers=auth_headers(token))
        assert resp.status_code == 403


def test_company_margin_report_aggregates_recent_invoices(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    product = _make_product(client, headers, price=100, cost=60)
    quote = _quote_with_mixed_items(client, headers, project, product)
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers)

    resp = client.get("/api/reports/margin", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["revenue"] == 250
    assert data["cost"] == 120
    assert data["basis"] == "facturado"


def test_company_margin_report_forbidden_for_non_admin(client, oficina_token, tecnico_token):
    for token in (oficina_token, tecnico_token):
        resp = client.get("/api/reports/margin", headers=auth_headers(token))
        assert resp.status_code == 403
