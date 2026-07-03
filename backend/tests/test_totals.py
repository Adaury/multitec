from app.services.totals import LineInput, compute_totals, line_subtotal


def test_line_subtotal_multiplies_and_rounds():
    assert line_subtotal(2, 15.5) == 31.0
    assert line_subtotal(3, 33.333) == 100.0


def test_compute_totals_applies_itbis_18_percent():
    items = [LineInput(quantity=2, unit_price=100), LineInput(quantity=1, unit_price=50)]
    subtotal, itbis, total = compute_totals(items, 0.18)
    assert subtotal == 250.0
    assert itbis == 45.0
    assert total == 295.0


def test_compute_totals_empty_items():
    subtotal, itbis, total = compute_totals([], 0.18)
    assert (subtotal, itbis, total) == (0.0, 0.0, 0.0)
