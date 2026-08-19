from tests.conftest import auth_headers, make_category, make_project, seed_ncf_sequence


def _approved_quote(client, headers, project):
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "NVR 8 canales", "quantity": 1, "unit_price": 250}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()
    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    return quote


def test_only_admin_can_convert_pre_invoice_to_invoice(client, admin_token, oficina_token, db_session):
    admin_headers = auth_headers(admin_token)
    oficina_headers = auth_headers(oficina_token)
    seed_ncf_sequence(db_session, ncf_type="B02")

    project = make_project(client, admin_headers)
    quote = _approved_quote(client, admin_headers, project)

    # oficina puede crear/ver prefacturas, pero no convertirlas a factura
    pre_invoice_resp = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=oficina_headers)
    assert pre_invoice_resp.status_code == 201
    pre_invoice = pre_invoice_resp.json()
    assert pre_invoice["total"] == quote["total"]

    forbidden = client.post(
        f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=oficina_headers
    )
    assert forbidden.status_code == 403

    allowed = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=admin_headers)
    assert allowed.status_code == 201
    assert allowed.json()["total"] == pre_invoice["total"]
    assert allowed.json()["code"] == "FAC-000001"
    # cliente de prueba no tiene RNC -> B02 (consumo) por defecto
    assert allowed.json()["ncf"] == "B0200000001"
    assert allowed.json()["ncf_type"] == "B02"

    # ya facturada: una segunda conversión debe fallar
    again = client.post(f"/api/pre-invoices/{pre_invoice['id']}/convert-to-invoice", headers=admin_headers)
    assert again.status_code == 400


def test_cannot_generate_pre_invoice_from_unapproved_quote(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cable UTP cat6", "quantity": 100, "unit_price": 1.5}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()

    resp = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers)
    assert resp.status_code == 400


def test_create_pre_invoice_uses_configured_itbis_rate(client, admin_token, monkeypatch):
    import app.api.routers.invoices as invoices_module

    base_settings = invoices_module.get_settings()
    custom_settings = base_settings.model_copy(update={"itbis_rate": 0.10})
    monkeypatch.setattr(invoices_module, "get_settings", lambda: custom_settings)

    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    resp = client.post(
        f"/api/projects/{project['id']}/pre-invoices",
        json={"items": [{"description": "Servicio manual", "quantity": 1, "unit_price": 100}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["subtotal"] == 100
    assert body["itbis"] == 10  # 10%, no el 18% hardcodeado
    assert body["total"] == 110


def test_pre_invoice_item_respects_explicit_zero_price(client, admin_token):
    """Un producto de catálogo con unit_price=0 explícito (ej. garantía/regalo) no debe
    sobreescribirse con el precio del catálogo."""
    headers = auth_headers(admin_token)
    category = make_category(client, headers)
    product = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cámara de regalo", "unit": "unidad", "price": 200},
        headers=headers,
    ).json()
    project = make_project(client, headers)

    resp = client.post(
        f"/api/projects/{project['id']}/pre-invoices",
        json={"items": [{"product_id": product["id"], "description": "", "quantity": 1, "unit_price": 0}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["items"][0]["unit_price"] == 0
    assert resp.json()["total"] == 0


def test_pre_invoice_item_without_price_falls_back_to_catalog_price(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers)
    product = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cámara IP", "unit": "unidad", "price": 200},
        headers=headers,
    ).json()
    project = make_project(client, headers)

    resp = client.post(
        f"/api/projects/{project['id']}/pre-invoices",
        json={"items": [{"product_id": product["id"], "description": "", "quantity": 1}]},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["items"][0]["unit_price"] == 200


def test_pre_invoice_item_rejects_negative_quantity_and_price(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    negative_qty = client.post(
        f"/api/projects/{project['id']}/pre-invoices",
        json={"items": [{"description": "x", "quantity": -1, "unit_price": 10}]},
        headers=headers,
    )
    assert negative_qty.status_code == 422

    negative_price = client.post(
        f"/api/projects/{project['id']}/pre-invoices",
        json={"items": [{"description": "x", "quantity": 1, "unit_price": -10}]},
        headers=headers,
    )
    assert negative_price.status_code == 422
