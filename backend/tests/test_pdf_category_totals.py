from types import SimpleNamespace

from app.services.pdf import FALLBACK_CATEGORY_LABEL, _category_totals


def _item(product_id, subtotal):
    return SimpleNamespace(product_id=product_id, subtotal=subtotal)


def test_groups_and_sums_by_category():
    items = [_item(1, 100.0), _item(2, 50.0), _item(3, 25.0)]
    category_by_product_id = {1: "CCTV", 2: "CCTV", 3: "Redes"}

    result = _category_totals(items, category_by_product_id)

    assert result == [("CCTV", 150.0), ("Redes", 25.0)]


def test_items_without_known_category_fall_back():
    items = [_item(None, 200.0)]

    result = _category_totals(items, {})

    assert result == [(FALLBACK_CATEGORY_LABEL, 200.0)]


def test_preserves_first_seen_category_order():
    items = [_item(2, 10.0), _item(1, 20.0), _item(2, 5.0)]
    category_by_product_id = {1: "Redes", 2: "CCTV"}

    result = _category_totals(items, category_by_product_id)

    assert [name for name, _ in result] == ["CCTV", "Redes"]
