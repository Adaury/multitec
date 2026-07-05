from tests.conftest import auth_headers, make_category, make_project


def _create_product(client, headers, category_id=None, **overrides):
    if category_id is None:
        category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Cámara IP", "unit": "unidad", "price": 150}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def _pending_quote(client, headers, project, items):
    budget = client.post(
        f"/api/projects/{project['id']}/budgets", json={"items": items}, headers=headers
    ).json()
    return client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()


def test_purchase_list_preview_before_approval_creates_nothing(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers)
    quote = _pending_quote(
        client, headers, project, [{"product_id": camera["id"], "description": camera["name"], "quantity": 4, "unit_price": 150}]
    )

    resp = client.get(f"/api/quotes/{quote['id']}/purchase-list-preview", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["already_generated"] is False
    assert body["items"] == [{"product_id": camera["id"], "description": camera["name"], "quantity": 4}]

    # Solo lectura: la cotización sigue pendiente y no se generaron Materiales.
    assert client.get(f"/api/quotes/{quote['id']}", headers=headers).json()["status"] == "pendiente"
    materials = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()
    assert materials == []


def test_purchase_list_preview_matches_what_approval_actually_creates(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers)
    quote = _pending_quote(
        client, headers, project, [{"product_id": camera["id"], "description": camera["name"], "quantity": 4, "unit_price": 150}]
    )

    preview = client.get(f"/api/quotes/{quote['id']}/purchase-list-preview", headers=headers).json()

    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    materials = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()

    assert len(materials) == 1
    assert preview["items"][0]["product_id"] == materials[0]["product_id"]
    assert preview["items"][0]["description"] == materials[0]["description"]
    assert preview["items"][0]["quantity"] == materials[0]["quantity"]

    # Después de aprobar, la vista previa refleja que ya se generó.
    preview_after = client.get(f"/api/quotes/{quote['id']}/purchase-list-preview", headers=headers).json()
    assert preview_after["already_generated"] is True


def test_executive_quote_pdf_groups_by_category(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    camera = _create_product(client, headers, category_id=camera_category, name="Cámara IP")
    quote = _pending_quote(
        client,
        headers,
        project,
        [
            {"product_id": camera["id"], "description": camera["name"], "quantity": 4, "unit_price": 150},
            {"product_id": None, "description": "Mano de obra instalación", "quantity": 1, "unit_price": 200},
        ],
    )

    detailed = client.get(f"/api/quotes/{quote['id']}/pdf", headers=headers)
    assert detailed.status_code == 200
    assert detailed.content[:4] == b"%PDF"

    executive = client.get(f"/api/quotes/{quote['id']}/pdf?variant=ejecutiva", headers=headers)
    assert executive.status_code == 200
    assert executive.headers["content-type"] == "application/pdf"
    assert executive.content[:4] == b"%PDF"
    assert f'{quote["code"]}-ejecutiva.pdf' in executive.headers["content-disposition"]
    assert executive.content != detailed.content

    invalid = client.get(f"/api/quotes/{quote['id']}/pdf?variant=otra", headers=headers)
    assert invalid.status_code == 422
