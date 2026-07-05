from tests.conftest import auth_headers, make_category


def test_create_product_with_labor_and_cost_fields(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers)

    resp = client.post(
        "/api/catalog",
        json={
            "category_id": category["id"],
            "name": "Cámara IP",
            "unit": "unidad",
            "price": 150,
            "cost": 90,
            "install_minutes": 45,
            "labor_role": "técnico CCTV",
            "priority": 2,
        },
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cost"] == 90
    assert body["install_minutes"] == 45
    assert body["labor_role"] == "técnico CCTV"
    assert body["priority"] == 2


def test_create_product_defaults_new_fields_when_omitted(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers)

    resp = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "Cable UTP", "unit": "metro", "price": 2},
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["cost"] == 0
    assert body["install_minutes"] is None
    assert body["labor_role"] is None
    assert body["priority"] is None


def test_update_product_sets_labor_fields_without_touching_others(client, admin_token):
    headers = auth_headers(admin_token)
    category = make_category(client, headers)
    product = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": "NVR 8 canales", "unit": "unidad", "price": 400},
        headers=headers,
    ).json()

    resp = client.put(
        f"/api/catalog/{product['id']}",
        json={"install_minutes": 60, "labor_role": "técnico CCTV senior"},
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["install_minutes"] == 60
    assert body["labor_role"] == "técnico CCTV senior"
    assert body["price"] == 400  # sin tocar por la actualización parcial
    assert body["cost"] == 0
