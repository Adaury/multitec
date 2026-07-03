from tests.conftest import auth_headers, make_project, seed_ncf_sequence


def _approved_budget_items(client, headers, project):
    return client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cámara IP", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    ).json()


def test_generate_and_access_public_link(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Portal Test Client")

    link = client.post(f"/api/projects/{project['id']}/public-link", headers=headers)
    assert link.status_code == 200
    token = link.json()["token"]
    assert len(token) > 20

    public = client.get(f"/api/public/projects/{token}")
    assert public.status_code == 200
    body = public.json()
    assert body["code"] == project["code"]
    assert body["client_name"] == "Portal Test Client"
    assert body["quotes"] == []
    assert body["invoices"] == []


def test_public_portal_requires_no_auth(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    # sin ningún header de Authorization
    public = client.get(f"/api/public/projects/{token}")
    assert public.status_code == 200


def test_invalid_token_returns_404(client):
    resp = client.get("/api/public/projects/token-que-no-existe")
    assert resp.status_code == 404


def test_regenerating_link_invalidates_old_token(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    first = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]
    second = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]
    assert first != second

    assert client.get(f"/api/public/projects/{first}").status_code == 404
    assert client.get(f"/api/public/projects/{second}").status_code == 200


def test_revoking_link_disables_portal(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    revoke = client.delete(f"/api/projects/{project['id']}/public-link", headers=headers)
    assert revoke.status_code == 204
    assert client.get(f"/api/public/projects/{token}").status_code == 404


def test_public_portal_shows_quotes_and_invoices(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    budget = _approved_budget_items(client, headers, project)
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()

    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]
    public = client.get(f"/api/public/projects/{token}").json()

    assert len(public["quotes"]) == 1
    assert public["quotes"][0]["code"] == quote["code"]
    assert public["quotes"][0]["status"] == "aprobada"
    assert len(public["invoices"]) == 1
    assert public["invoices"][0]["ncf"] == invoice["ncf"]


def test_public_invoice_pdf_download(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")
    project = make_project(client, headers)
    budget = _approved_budget_items(client, headers, project)
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    pre_invoice = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers).json()
    invoice = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=headers).json()
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    resp = client.get(f"/api/public/projects/{token}/invoices/{invoice['id']}/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


def test_public_invoice_pdf_rejects_invoice_from_another_project(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    seed_ncf_sequence(db_session, ncf_type="B02")

    # factura de un proyecto distinto al del token
    other_project = make_project(client, headers, client_name="Otro cliente")
    other_budget = _approved_budget_items(client, headers, other_project)
    other_quote = client.post(f"/api/budgets/{other_budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{other_quote['id']}/approve", headers=headers)
    other_pre_invoice = client.post(
        f"/api/quotes/{other_quote['id']}/generate-pre-invoice", headers=headers
    ).json()
    other_invoice = client.post(
        f"/api/pre-invoices/{other_pre_invoice['id']}/convert-to-invoice", headers=headers
    ).json()

    project = make_project(client, headers, client_name="Proyecto del token")
    token = client.post(f"/api/projects/{project['id']}/public-link", headers=headers).json()["token"]

    resp = client.get(f"/api/public/projects/{token}/invoices/{other_invoice['id']}/pdf")
    assert resp.status_code == 404


def test_only_admin_or_oficina_can_manage_public_link(client, tecnico_token, admin_token):
    admin_headers = auth_headers(admin_token)
    project = make_project(client, admin_headers)

    resp = client.post(f"/api/projects/{project['id']}/public-link", headers=auth_headers(tecnico_token))
    assert resp.status_code == 403
