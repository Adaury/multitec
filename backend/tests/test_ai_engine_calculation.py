from app.ai_engine.calculation import apply_cable_waste_margin, build_labor_budget_item, calculate_labor

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


def test_calculate_labor_sums_hours_across_items():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 8},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 1},
    ]
    install_profiles = {1: (30.0, "técnico CCTV"), 2: (60.0, "técnico CCTV")}

    estimate = calculate_labor(items, install_profiles, hourly_rate=200, max_hours_per_technician=40)

    # 8 * 30min = 240min + 1 * 60min = 300min -> 5 horas
    assert estimate["total_hours"] == 5.0
    assert estimate["labor_cost"] == 1000.0  # 5h * 200
    assert estimate["technician_count"] == 1


def test_calculate_labor_returns_none_when_nothing_has_install_minutes():
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 8}]
    install_profiles = {1: (None, "técnico CCTV")}

    estimate = calculate_labor(items, install_profiles, hourly_rate=200, max_hours_per_technician=40)

    assert estimate is None


def test_calculate_labor_ignores_items_without_a_matching_product():
    items = [{"product_id": None, "description": "Instalación mencionada a mano", "quantity": 1}]

    estimate = calculate_labor(items, {}, hourly_rate=200, max_hours_per_technician=40)

    assert estimate is None


def test_calculate_labor_adds_a_second_technician_past_the_threshold():
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 100}]
    install_profiles = {1: (30.0, "técnico CCTV")}  # 100 * 30min = 3000min = 50h

    estimate = calculate_labor(items, install_profiles, hourly_rate=200, max_hours_per_technician=40)

    assert estimate["total_hours"] == 50.0
    assert estimate["technician_count"] == 2  # ceil(50 / 40)
    assert estimate["labor_cost"] == 10000.0  # el costo no se divide entre técnicos


def test_calculate_labor_breaks_down_hours_by_role():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 4},
        {"product_id": 2, "description": "Panel eléctrico", "quantity": 1},
    ]
    install_profiles = {1: (30.0, "técnico CCTV"), 2: (120.0, "electricista")}

    estimate = calculate_labor(items, install_profiles, hourly_rate=200, max_hours_per_technician=40)

    assert estimate["hours_by_role"] == {"técnico CCTV": 2.0, "electricista": 2.0}


def test_build_labor_budget_item_shape():
    estimate = {
        "total_hours": 5.0,
        "technician_count": 1,
        "hourly_rate": 200,
        "labor_cost": 1000.0,
        "hours_by_role": {"técnico CCTV": 5.0},
    }

    item = build_labor_budget_item(estimate)

    assert item["product_id"] is None
    assert item["quantity"] == 5.0
    assert item["unit_price"] == 200
    assert "Mano de obra de instalación" in item["description"]
    assert "técnico CCTV" in item["description"]
