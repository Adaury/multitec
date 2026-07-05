from tests.conftest import auth_headers, make_category


def _create_product(client, headers, category_id=None, **overrides):
    if category_id is None:
        category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Producto", "unit": "unidad", "price": 100}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_product_relation(client, admin_token):
    headers = auth_headers(admin_token)
    switch = _create_product(client, headers, name="Switch PoE 8p")
    source = _create_product(client, headers, name="Fuente 12V 5A")

    resp = client.post(
        f"/api/catalog/{switch['id']}/relations",
        json={"related_product_id": source["id"], "relation_type": "requiere", "notes": "Alimentación externa"},
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["product_id"] == switch["id"]
    assert body["related_product_id"] == source["id"]
    assert body["relation_type"] == "requiere"
    assert body["notes"] == "Alimentación externa"


def test_create_relation_rejects_self_relation(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)

    resp = client.post(
        f"/api/catalog/{product['id']}/relations",
        json={"related_product_id": product["id"], "relation_type": "compatible_con"},
        headers=headers,
    )

    assert resp.status_code == 400


def test_create_relation_rejects_unknown_related_product(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)

    resp = client.post(
        f"/api/catalog/{product['id']}/relations",
        json={"related_product_id": 999999, "relation_type": "compatible_con"},
        headers=headers,
    )

    assert resp.status_code == 400


def test_create_relation_rejects_unknown_relation_type(client, admin_token):
    headers = auth_headers(admin_token)
    a = _create_product(client, headers, name="A")
    b = _create_product(client, headers, name="B")

    resp = client.post(
        f"/api/catalog/{a['id']}/relations",
        json={"related_product_id": b["id"], "relation_type": "no_existe"},
        headers=headers,
    )

    assert resp.status_code == 422


def test_relation_is_visible_from_both_products_with_correct_direction(client, admin_token):
    headers = auth_headers(admin_token)
    switch = _create_product(client, headers, name="Switch PoE 8p")
    source = _create_product(client, headers, name="Fuente 12V 5A")

    client.post(
        f"/api/catalog/{switch['id']}/relations",
        json={"related_product_id": source["id"], "relation_type": "requiere"},
        headers=headers,
    )

    from_switch = client.get(f"/api/catalog/{switch['id']}/relations", headers=headers).json()
    assert len(from_switch) == 1
    assert from_switch[0]["direction"] == "outgoing"
    assert from_switch[0]["related_product_id"] == source["id"]
    assert from_switch[0]["related_product_name"] == "Fuente 12V 5A"

    from_source = client.get(f"/api/catalog/{source['id']}/relations", headers=headers).json()
    assert len(from_source) == 1
    assert from_source[0]["direction"] == "incoming"
    assert from_source[0]["related_product_id"] == switch["id"]
    assert from_source[0]["related_product_name"] == "Switch PoE 8p"


def test_update_relation_type_and_notes(client, admin_token):
    headers = auth_headers(admin_token)
    a = _create_product(client, headers, name="A")
    b = _create_product(client, headers, name="B")
    relation = client.post(
        f"/api/catalog/{a['id']}/relations",
        json={"related_product_id": b["id"], "relation_type": "compatible_con"},
        headers=headers,
    ).json()

    resp = client.put(
        f"/api/catalog/relations/{relation['id']}",
        json={"relation_type": "alternativa_de", "notes": "Reemplazo directo"},
        headers=headers,
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["relation_type"] == "alternativa_de"
    assert body["notes"] == "Reemplazo directo"


def test_delete_relation(client, admin_token):
    headers = auth_headers(admin_token)
    a = _create_product(client, headers, name="A")
    b = _create_product(client, headers, name="B")
    relation = client.post(
        f"/api/catalog/{a['id']}/relations",
        json={"related_product_id": b["id"], "relation_type": "compatible_con"},
        headers=headers,
    ).json()

    resp = client.delete(f"/api/catalog/relations/{relation['id']}", headers=headers)
    assert resp.status_code == 204

    assert client.get(f"/api/catalog/{a['id']}/relations", headers=headers).json() == []
    assert client.get(f"/api/catalog/{b['id']}/relations", headers=headers).json() == []


def test_tecnico_cannot_write_relations(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    tecnico_headers = auth_headers(tecnico_token)
    a = _create_product(client, admin_headers, name="A")
    b = _create_product(client, admin_headers, name="B")

    resp = client.post(
        f"/api/catalog/{a['id']}/relations",
        json={"related_product_id": b["id"], "relation_type": "compatible_con"},
        headers=tecnico_headers,
    )
    assert resp.status_code == 403

    # allowed_roles del router de catálogo es admin+oficina, igual que rules/technical-rules
    read_resp = client.get(f"/api/catalog/{a['id']}/relations", headers=tecnico_headers)
    assert read_resp.status_code == 403
