from tests.conftest import auth_headers, make_project


def _make_supplier(client, headers, name="Distribuidora ABC"):
    resp = client.post("/api/suppliers", json={"name": name, "rnc": "101234567"}, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_list_get_update_supplier(client, admin_token):
    headers = auth_headers(admin_token)

    create_resp = client.post(
        "/api/suppliers",
        json={"name": "Distribuidora ABC", "rnc": "101234567", "phone": "8095551111"},
        headers=headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    supplier_id = create_resp.json()["id"]

    list_resp = client.get("/api/suppliers", headers=headers)
    assert list_resp.status_code == 200
    assert any(s["id"] == supplier_id for s in list_resp.json())

    get_resp = client.get(f"/api/suppliers/{supplier_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Distribuidora ABC"

    update_resp = client.put(
        f"/api/suppliers/{supplier_id}",
        json={"name": "Distribuidora ABC Actualizada", "rnc": "101234567"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Distribuidora ABC Actualizada"


def test_get_unknown_supplier_404(client, admin_token):
    resp = client.get("/api/suppliers/999999", headers=auth_headers(admin_token))
    assert resp.status_code == 404


def test_suppliers_forbidden_for_tecnico(client, tecnico_token):
    headers = auth_headers(tecnico_token)
    assert client.get("/api/suppliers", headers=headers).status_code == 403
    assert client.post("/api/suppliers", json={"name": "X"}, headers=headers).status_code == 403
    assert client.get("/api/suppliers/1/materials", headers=headers).status_code == 403


def test_marking_material_purchased_records_supplier_and_price(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    supplier = _make_supplier(client, headers)

    material = client.post(
        f"/api/projects/{project['id']}/materials",
        json={"description": "Cable UTP cat6", "quantity": 3},
        headers=headers,
    ).json()

    resp = client.put(
        f"/api/materials/{material['id']}/status",
        json={"status": "comprado", "supplier_id": supplier["id"], "purchase_price": 45.5},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "comprado"
    assert data["supplier_id"] == supplier["id"]
    assert data["supplier_name"] == "Distribuidora ABC"
    assert data["purchase_price"] == 45.5

    materials_list = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()
    listed = next(m for m in materials_list if m["id"] == material["id"])
    assert listed["supplier_name"] == "Distribuidora ABC"
    assert listed["purchase_price"] == 45.5


def test_status_update_without_supplier_fields_keeps_existing_values(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    supplier = _make_supplier(client, headers)

    material = client.post(
        f"/api/projects/{project['id']}/materials",
        json={"description": "NVR 8 canales", "quantity": 1},
        headers=headers,
    ).json()
    client.put(
        f"/api/materials/{material['id']}/status",
        json={"status": "comprado", "supplier_id": supplier["id"], "purchase_price": 3000},
        headers=headers,
    )

    resp = client.put(
        f"/api/materials/{material['id']}/status",
        json={"status": "instalado"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "instalado"
    assert data["supplier_id"] == supplier["id"]
    assert data["purchase_price"] == 3000


def test_supplier_purchase_history_spans_multiple_projects(client, admin_token):
    headers = auth_headers(admin_token)
    supplier = _make_supplier(client, headers)
    project_a = make_project(client, headers, client_name="Cliente A")
    project_b = make_project(client, headers, client_name="Cliente B")

    material_a = client.post(
        f"/api/projects/{project_a['id']}/materials",
        json={"description": "Cámara IP", "quantity": 2},
        headers=headers,
    ).json()
    material_b = client.post(
        f"/api/projects/{project_b['id']}/materials",
        json={"description": "Switch PoE", "quantity": 1},
        headers=headers,
    ).json()

    client.put(
        f"/api/materials/{material_a['id']}/status",
        json={"status": "comprado", "supplier_id": supplier["id"], "purchase_price": 60},
        headers=headers,
    )
    client.put(
        f"/api/materials/{material_b['id']}/status",
        json={"status": "comprado", "supplier_id": supplier["id"], "purchase_price": 3200},
        headers=headers,
    )

    resp = client.get(f"/api/suppliers/{supplier['id']}/materials", headers=headers)
    assert resp.status_code == 200, resp.text
    history = resp.json()
    assert len(history) == 2
    project_codes = {row["project_code"] for row in history}
    assert project_codes == {project_a["code"], project_b["code"]}
