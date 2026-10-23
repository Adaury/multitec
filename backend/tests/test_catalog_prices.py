from tests.conftest import auth_headers, make_category


def _product(client, token, category, name="Cámara", price=0):
    res = client.post(
        "/api/catalog",
        json={"category_id": category["id"], "name": name, "price": price},
        headers=auth_headers(token),
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_bulk_prices_updates_all_and_clears_estimated_flag(client, db_session, admin_token):
    from app.models.product import Product

    category = make_category(client, auth_headers(admin_token))
    a = _product(client, admin_token, category, "A")
    b = _product(client, admin_token, category, "B")
    db_session.query(Product).update({"price_estimated": True})
    db_session.commit()

    res = client.put(
        "/api/catalog/bulk-prices",
        json={"items": [{"id": a["id"], "price": 100}, {"id": b["id"], "price": 250.5}]},
        headers=auth_headers(admin_token),
    )

    assert res.status_code == 200, res.text
    assert [p["price"] for p in res.json()] == [100, 250.5]
    assert all(p["price_estimated"] is False for p in res.json())


def test_bulk_prices_is_all_or_nothing_when_a_product_is_missing(client, db_session, admin_token):
    category = make_category(client, auth_headers(admin_token))
    a = _product(client, admin_token, category, "A", price=10)

    res = client.put(
        "/api/catalog/bulk-prices",
        json={"items": [{"id": a["id"], "price": 99}, {"id": 999999, "price": 1}]},
        headers=auth_headers(admin_token),
    )

    assert res.status_code == 404
    listed = client.get("/api/catalog", headers=auth_headers(admin_token)).json()
    assert listed[0]["price"] == 10


def test_bulk_prices_is_admin_only(client, db_session, oficina_token):
    res = client.put(
        "/api/catalog/bulk-prices",
        json={"items": [{"id": 1, "price": 5}]},
        headers=auth_headers(oficina_token),
    )
    assert res.status_code == 403


def test_editing_price_of_one_product_clears_estimated_but_other_edits_do_not(client, db_session, admin_token):
    from app.models.product import Product

    category = make_category(client, auth_headers(admin_token))
    p = _product(client, admin_token, category, "A", price=10)
    db_session.query(Product).update({"price_estimated": True})
    db_session.commit()
    headers = auth_headers(admin_token)

    client.put(f"/api/catalog/{p['id']}", json={"price": 10, "name": "A2"}, headers=headers)
    assert client.get("/api/catalog", headers=headers).json()[0]["price_estimated"] is True

    client.put(f"/api/catalog/{p['id']}", json={"price": 12}, headers=headers)
    assert client.get("/api/catalog", headers=headers).json()[0]["price_estimated"] is False
