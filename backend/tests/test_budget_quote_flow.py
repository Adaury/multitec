from tests.conftest import auth_headers, make_project


def test_budget_to_quote_to_material_flow(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    budget_resp = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={
            "notes": "Presupuesto inicial",
            "items": [{"description": "Cámara domo 4MP", "quantity": 4, "unit_price": 100}],
        },
        headers=headers,
    )
    assert budget_resp.status_code == 201
    budget = budget_resp.json()
    assert budget["code"] == "PRE-000001"
    assert budget["total"] == 400.0
    # regla de negocio: la salida pública de presupuesto NO expone unit_price
    assert "unit_price" not in budget["items"][0]

    quote_resp = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers)
    assert quote_resp.status_code == 201
    quote = quote_resp.json()
    assert quote["code"] == "COT-000001"
    assert quote["subtotal"] == 400.0
    assert quote["itbis"] == 72.0
    assert quote["total"] == 472.0
    assert quote["status"] == "pendiente"

    approve_resp = client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "aprobada"

    materials_resp = client.get(f"/api/projects/{project['id']}/materials", headers=headers)
    assert materials_resp.status_code == 200
    materials = materials_resp.json()
    assert len(materials) == 1
    assert materials[0]["quantity"] == 4
    assert materials[0]["status"] == "pendiente_compra"

    # § levantamiento inteligente: aprobar ya genera la prefactura sola, sin que nadie la
    # tenga que pedir a mano — copia los mismos totales/items que la cotización aprobada.
    pre_invoices = client.get(f"/api/projects/{project['id']}/pre-invoices", headers=headers).json()
    assert len(pre_invoices) == 1
    assert pre_invoices[0]["source_quote_id"] == quote["id"]
    assert pre_invoices[0]["total"] == quote["total"]

    # generate-pre-invoice manual, llamado después, debe devolver la misma prefactura en
    # vez de crear una segunda (idempotencia compartida con la generación automática).
    manual_resp = client.post(f"/api/quotes/{quote['id']}/generate-pre-invoice", headers=headers)
    assert manual_resp.status_code == 201
    assert manual_resp.json()["id"] == pre_invoices[0]["id"]
    assert len(client.get(f"/api/projects/{project['id']}/pre-invoices", headers=headers).json()) == 1


def test_approving_quote_twice_does_not_duplicate_materials_or_pre_invoice(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "NVR 8 canales", "quantity": 1, "unit_price": 250}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()

    client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    client.post(f"/api/quotes/{quote['id']}/archive", headers=headers)
    reactivate_resp = client.post(f"/api/quotes/{quote['id']}/reactivate", headers=headers)
    assert reactivate_resp.status_code == 200
    assert reactivate_resp.json()["status"] == "pendiente"

    reapprove_resp = client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    assert reapprove_resp.status_code == 200

    materials = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()
    assert len(materials) == 1

    pre_invoices = client.get(f"/api/projects/{project['id']}/pre-invoices", headers=headers).json()
    assert len(pre_invoices) == 1


def test_reject_quote(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Switch 24 puertos", "quantity": 1, "unit_price": 300}]},
        headers=headers,
    ).json()
    quote = client.post(f"/api/budgets/{budget['id']}/convert-to-quote", headers=headers).json()

    reject_resp = client.post(
        f"/api/quotes/{quote['id']}/reject", json={"reason": "Presupuesto excede lo aprobado"}, headers=headers
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "no_aprobada"

    # una cotización rechazada no se puede volver a aprobar directamente
    approve_resp = client.post(f"/api/quotes/{quote['id']}/approve", headers=headers)
    assert approve_resp.status_code == 400
