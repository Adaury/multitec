from app.ai_engine.calculation import apply_cable_waste_margin

CATALOG = [
    {"id": 1, "name": "Cable UTP Cat6", "tags": ["cable", "utp"]},
    {"id": 2, "name": "Cámara IP", "tags": ["camara"]},
]


def test_cable_item_quantity_increases_by_margin():
    items = [{"product_id": 1, "description": "Cable UTP Cat6", "quantity": 200}]

    result = apply_cable_waste_margin(items, CATALOG, 0.05)

    assert result[0]["quantity"] == 210.0


def test_non_cable_item_is_untouched():
    items = [{"product_id": 2, "description": "Cámara IP", "quantity": 8}]

    result = apply_cable_waste_margin(items, CATALOG, 0.05)

    assert result[0]["quantity"] == 8


def test_zero_margin_returns_items_unchanged():
    items = [{"product_id": 1, "description": "Cable UTP Cat6", "quantity": 200}]

    result = apply_cable_waste_margin(items, CATALOG, 0)

    assert result[0]["quantity"] == 200


def test_item_without_product_id_is_untouched():
    items = [{"product_id": None, "description": "Instalación", "quantity": 1}]

    result = apply_cable_waste_margin(items, CATALOG, 0.05)

    assert result[0]["quantity"] == 1


def test_rounds_to_two_decimals():
    items = [{"product_id": 1, "description": "Cable UTP Cat6", "quantity": 33}]

    result = apply_cable_waste_margin(items, CATALOG, 0.1)  # 33 * 1.1 = 36.3

    assert result[0]["quantity"] == 36.3
