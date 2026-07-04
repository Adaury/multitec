from tests.conftest import auth_headers


def _create_product(client, headers, name="Cámara IP 4MP"):
    return client.post(
        "/api/catalog", json={"category": "camara", "name": name, "unit": "unidad", "price": 100}, headers=headers
    ).json()


def test_new_product_starts_with_zero_stock(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    assert product["stock_quantity"] == 0


def test_entrada_increases_stock(client, admin_token, oficina_token):
    admin_headers = auth_headers(admin_token)
    product = _create_product(client, admin_headers)

    # oficina puede registrar movimientos, no solo admin
    resp = client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "entrada", "quantity": 10, "reason": "Compra a proveedor"},
        headers=auth_headers(oficina_token),
    )
    assert resp.status_code == 201
    assert resp.json()["quantity"] == 10

    updated = client.get("/api/catalog", headers=admin_headers).json()
    updated_product = next(p for p in updated if p["id"] == product["id"])
    assert updated_product["stock_quantity"] == 10


def test_salida_decreases_stock(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "entrada", "quantity": 10},
        headers=headers,
    )

    resp = client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "salida", "quantity": 4, "reason": "Instalación proyecto X"},
        headers=headers,
    )
    assert resp.status_code == 201

    updated = client.get("/api/catalog", headers=headers).json()
    updated_product = next(p for p in updated if p["id"] == product["id"])
    assert updated_product["stock_quantity"] == 6


def test_salida_exceeding_stock_is_rejected(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "entrada", "quantity": 5},
        headers=headers,
    )

    resp = client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "salida", "quantity": 10},
        headers=headers,
    )
    assert resp.status_code == 400
    assert "stock" in resp.json()["detail"].lower()

    # el stock no debe haber cambiado
    unchanged = client.get("/api/catalog", headers=headers).json()
    unchanged_product = next(p for p in unchanged if p["id"] == product["id"])
    assert unchanged_product["stock_quantity"] == 5


def test_stock_movement_history_is_listed_newest_first(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "entrada", "quantity": 5},
        headers=headers,
    )
    client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "salida", "quantity": 2},
        headers=headers,
    )

    history = client.get(f"/api/products/{product['id']}/stock-movements", headers=headers).json()
    assert len(history) == 2
    assert history[0]["movement_type"] == "salida"
    assert history[1]["movement_type"] == "entrada"


def test_tecnico_cannot_access_inventory(client, admin_token, tecnico_token):
    admin_headers = auth_headers(admin_token)
    product = _create_product(client, admin_headers)

    resp = client.post(
        f"/api/products/{product['id']}/stock-movements",
        json={"movement_type": "entrada", "quantity": 5},
        headers=auth_headers(tecnico_token),
    )
    assert resp.status_code == 403


def test_catalog_smart_fields_round_trip(client, admin_token):
    """§ catálogo inteligente: tags/sinónimos/sugiere y las descripciones/marca/modelo se
    guardan y regresan completos — son la base del matching semántico en el levantamiento."""
    headers = auth_headers(admin_token)
    resp = client.post(
        "/api/catalog",
        json={
            "category": "camara",
            "name": "Cámara domo IP 4MP",
            "unit": "unidad",
            "price": 150,
            "brand": "Hikvision",
            "model": "DS-2CD1343G0",
            "commercial_description": "Cámara domo para exteriores",
            "technical_description": "4MP, IR 30m, IP67",
            "tags": ["camara", "domo", "ip", "cctv"],
            "synonyms": ["camarita", "ojo"],
            "suggests_tags": ["nvr", "poe-switch"],
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    product = resp.json()
    assert product["brand"] == "Hikvision"
    assert product["model"] == "DS-2CD1343G0"
    assert set(product["tags"]) == {"camara", "domo", "ip", "cctv"}
    assert set(product["synonyms"]) == {"camarita", "ojo"}
    assert set(product["suggests_tags"]) == {"nvr", "poe-switch"}

    # una fila vieja/sin etiquetar (sin tags) debe salir como [] y no como null
    plain = _create_product(client, headers, name="Producto sin etiquetas")
    assert plain["tags"] == []
    assert plain["synonyms"] == []
    assert plain["suggests_tags"] == []
