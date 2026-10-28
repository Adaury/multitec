from tests.conftest import auth_headers, make_category, make_project


def _product(client, headers, name, price):
    category = make_category(client, headers, name=f"Cat {name}", code_prefix=name[:3].upper())
    resp = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": name, "unit": "unidad", "price": price},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _quote(client, headers, project_id, cam, nvr):
    resp = client.post(
        f"/api/projects/{project_id}/quotes",
        json={
            "items": [
                {"product_id": cam["id"], "description": cam["name"], "quantity": 4},
                {"product_id": nvr["id"], "description": nvr["name"], "quantity": 1},
                {"description": "Mano de obra (texto libre)", "quantity": 1, "unit_price": 5000},
            ]
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _raise_price(client, headers, product, new_price):
    resp = client.put(f"/api/catalog/{product['id']}", json={"price": new_price}, headers=headers)
    assert resp.status_code == 200, resp.text


def test_reprice_pending_quote_updates_in_place_and_logs_history(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    cam, nvr = _product(client, h, "Camara IP", 100), _product(client, h, "NVR 8ch", 1000)
    quote = _quote(client, h, project["id"], cam, nvr)

    # Sin cambios en el catálogo no hay nada que actualizar
    assert client.get(f"/api/quotes/{quote['id']}/reprice-preview", headers=h).json()["changes"] == []
    assert client.post(f"/api/quotes/{quote['id']}/reprice", headers=h).status_code == 400

    _raise_price(client, h, cam, 150)
    preview = client.get(f"/api/quotes/{quote['id']}/reprice-preview", headers=h).json()
    assert [(c["old_price"], c["new_price"], c["quantity"]) for c in preview["changes"]] == [(100.0, 150.0, 4.0)]
    assert preview["total_new"] > preview["total_old"]

    out = client.post(f"/api/quotes/{quote['id']}/reprice", headers=h).json()
    assert out["created_new"] is False and out["quote"]["id"] == quote["id"]
    lines = {i["description"]: i for i in out["quote"]["items"]}
    assert lines["Camara IP"]["unit_price"] == 150 and lines["Camara IP"]["subtotal"] == 600
    assert lines["Mano de obra (texto libre)"]["unit_price"] == 5000  # el texto libre no se toca
    assert out["quote"]["total"] == round((600 + 1000 + 5000) * 1.18, 2)

    history = client.get(f"/api/quotes/{quote['id']}/history", headers=h).json()
    assert history[-1]["action"] == "repreciada" and "1 precio" in history[-1]["note"]


def test_reprice_approved_quote_creates_a_new_pending_version_and_leaves_the_original(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    cam, nvr = _product(client, h, "Camara IP", 100), _product(client, h, "NVR 8ch", 1000)
    quote = _quote(client, h, project["id"], cam, nvr)
    assert client.post(f"/api/quotes/{quote['id']}/approve", headers=h).status_code == 200
    _raise_price(client, h, nvr, 1200)

    out = client.post(f"/api/quotes/{quote['id']}/reprice", headers=h).json()
    assert out["created_new"] is True and out["quote"]["id"] != quote["id"]
    assert out["quote"]["status"] == "pendiente" and out["quote"]["code"] != quote["code"]
    assert next(i for i in out["quote"]["items"] if i["description"] == "NVR 8ch")["unit_price"] == 1200

    original = client.get(f"/api/quotes/{quote['id']}", headers=h).json()
    assert original["status"] == "aprobada" and original["total"] == quote["total"]
    assert next(i for i in original["items"] if i["description"] == "NVR 8ch")["unit_price"] == 1000
    assert client.get(f"/api/quotes/{quote['id']}/history", headers=h).json()[-1]["action"] == "nueva_version"


def test_new_version_copies_a_closed_quote_so_it_can_be_edited(client, admin_token):
    h = auth_headers(admin_token)
    project = make_project(client, h)
    cam, nvr = _product(client, h, "Camara IP", 100), _product(client, h, "NVR 8ch", 1000)
    quote = _quote(client, h, project["id"], cam, nvr)
    client.post(f"/api/quotes/{quote['id']}/reject", json={"reason": "caro"}, headers=h)
    assert client.put(f"/api/quotes/{quote['id']}", json={"items": []}, headers=h).status_code == 400  # cerrada

    new = client.post(f"/api/quotes/{quote['id']}/new-version", headers=h)
    assert new.status_code == 201
    body = new.json()
    assert body["status"] == "pendiente" and len(body["items"]) == 3 and body["total"] == quote["total"]
    edit = client.put(f"/api/quotes/{body['id']}", json={"items": [{"description": "Solo esto", "unit_price": 10}]}, headers=h)
    assert edit.status_code == 200


def test_a_catalog_price_of_zero_never_zeroes_a_quote_line(client, admin_token):
    """Un producto sin precio en el catálogo (0) no debe dejar la línea de la cotización en 0 al actualizar precios."""
    h = auth_headers(admin_token)
    project = make_project(client, h)
    cam, nvr = _product(client, h, "Camara IP", 100), _product(client, h, "NVR 8ch", 1000)
    quote = _quote(client, h, project["id"], cam, nvr)
    _raise_price(client, h, cam, 0)
    assert client.get(f"/api/quotes/{quote['id']}/reprice-preview", headers=h).json()["changes"] == []
    assert client.post(f"/api/quotes/{quote['id']}/reprice", headers=h).status_code == 400
