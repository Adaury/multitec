from tests.conftest import auth_headers, make_category


def test_create_and_list_categories(client, admin_token):
    headers = auth_headers(admin_token)
    parent = make_category(client, headers, name="CCTV", code_prefix=None)

    child_resp = client.post(
        "/api/categories",
        json={"name": "Cámaras IP", "parent_id": parent["id"], "code_prefix": "CAM"},
        headers=headers,
    )
    assert child_resp.status_code == 201, child_resp.text
    child = child_resp.json()
    assert child["parent_id"] == parent["id"]
    assert child["code_prefix"] == "CAM"
    assert child["slug"]  # autogenerado

    listed = client.get("/api/categories", headers=headers).json()
    ids = {c["id"] for c in listed}
    assert parent["id"] in ids and child["id"] in ids


def test_duplicate_name_gets_unique_slug(client, admin_token):
    headers = auth_headers(admin_token)
    first = make_category(client, headers, name="Redes")
    second = make_category(client, headers, name="Redes")
    assert first["slug"] != second["slug"]


def test_update_category_rename_and_reparent(client, admin_token):
    headers = auth_headers(admin_token)
    root_a = make_category(client, headers, name="Raíz A")
    root_b = make_category(client, headers, name="Raíz B")
    child = make_category(client, headers, name="Hijo")

    resp = client.put(
        f"/api/categories/{child['id']}",
        json={"name": "Hijo renombrado", "parent_id": root_a["id"]},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    updated = resp.json()
    assert updated["name"] == "Hijo renombrado"
    assert updated["parent_id"] == root_a["id"]

    # reparentar de nuevo, a otra raíz, debe funcionar sin problema
    resp2 = client.put(f"/api/categories/{child['id']}", json={"parent_id": root_b["id"]}, headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["parent_id"] == root_b["id"]


def test_cannot_create_cycle(client, admin_token):
    headers = auth_headers(admin_token)
    root = make_category(client, headers, name="Raíz")
    child = client.post(
        "/api/categories", json={"name": "Hijo", "parent_id": root["id"]}, headers=headers
    ).json()

    # intentar poner a la raíz como hija de su propio hijo -> ciclo, debe rechazarse
    resp = client.put(f"/api/categories/{root['id']}", json={"parent_id": child["id"]}, headers=headers)
    assert resp.status_code == 400


def test_delete_blocked_with_children(client, admin_token):
    headers = auth_headers(admin_token)
    parent = make_category(client, headers, name="Con hijos")
    client.post("/api/categories", json={"name": "Hijo", "parent_id": parent["id"]}, headers=headers)

    resp = client.delete(f"/api/categories/{parent['id']}", headers=headers)
    assert resp.status_code == 400


def test_delete_blocked_with_products(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers, name="Con productos")
    client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Producto", "unit": "unidad", "price": 10},
        headers=headers,
    )

    resp = client.delete(f"/api/categories/{category['id']}", headers=headers)
    assert resp.status_code == 400


def test_delete_leaf_category_without_products_succeeds(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers, name="Vacía y sin hijos")

    resp = client.delete(f"/api/categories/{category['id']}", headers=headers)
    assert resp.status_code == 204

    listed = client.get("/api/categories", headers=headers).json()
    assert category["id"] not in {c["id"] for c in listed}


def test_tecnico_can_read_but_not_write_categories(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    tecnico_headers = auth_headers(tecnico_token)

    read_resp = client.get("/api/categories", headers=tecnico_headers)
    assert read_resp.status_code == 200

    write_resp = client.post("/api/categories", json={"name": "No debería crear"}, headers=tecnico_headers)
    assert write_resp.status_code == 403

    category = make_category(client, admin_headers, name="Otra")
    delete_resp = client.delete(f"/api/categories/{category['id']}", headers=tecnico_headers)
    assert delete_resp.status_code == 403
