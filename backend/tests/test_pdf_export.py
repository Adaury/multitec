from tests.conftest import auth_headers, make_project, seed_ncf_sequence


def _approved_quote(client, headers, project):
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Switch PoE 8 puertos", "quantity": 1, "unit_price": 120}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    return quote


def test_quote_pdf_download(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    quote = _approved_quote(client, headers, project)

    resp = client.get(f"/api/quotes/{quote['id']}/pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert f'{quote["code"]}.pdf' in resp.headers["content-disposition"]


def test_invoice_pdf_download_includes_ncf(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    quote = _approved_quote(client, headers, project)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    resp = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_invoice_pdf_global_variant_hides_prices(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    quote = _approved_quote(client, headers, project)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    detailed = client.get(f"/api/invoices/{invoice['id']}/pdf", headers=headers)
    assert detailed.status_code == 200
    assert f'{invoice["code"]}.pdf' in detailed.headers["content-disposition"]

    global_pdf = client.get(f"/api/invoices/{invoice['id']}/pdf?variant=global", headers=headers)
    assert global_pdf.status_code == 200
    assert global_pdf.headers["content-type"] == "application/pdf"
    assert global_pdf.content[:4] == b"%PDF"
    assert f'{invoice["code"]}-global.pdf' in global_pdf.headers["content-disposition"]
    # documento distinto (sin precios/NCF) — no debería ser un byte-a-byte del detallado
    assert global_pdf.content != detailed.content

    invalid = client.get(f"/api/invoices/{invoice['id']}/pdf?variant=otra", headers=headers)
    assert invalid.status_code == 422


def test_tecnico_cannot_download_pdfs(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    tecnico_headers = auth_headers(tecnico_token)
    project = make_project(client, admin_headers)
    quote = _approved_quote(client, admin_headers, project)

    resp = client.get(f"/api/quotes/{quote['id']}/pdf", headers=tecnico_headers)
    assert resp.status_code == 403
