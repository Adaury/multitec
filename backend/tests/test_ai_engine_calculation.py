from app.ai_engine.calculation import (
    apply_cable_waste_margin,
    build_labor_budget_item,
    calculate_capacity_warnings,
    calculate_labor,
    calculate_storage,
)

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


def test_calculate_storage_bumps_disk_quantity_to_meet_real_capacity():
    items = [
        {"product_id": 1, "description": "Cámara IP 4MP", "quantity": 8},
        {"product_id": 2, "description": "Disco duro 2TB", "quantity": 1},  # regla ingenua: 1 disco fijo
    ]
    resolution_by_product_id = {1: 4.0}
    storage_capacity_by_product_id = {2: 2000.0}  # 2TB en GB

    # 8 cámaras * 4MP * 15 GB/MP/día * 30 días = 14400 GB -> ceil(14400/2000) = 8 discos
    result = calculate_storage(items, resolution_by_product_id, storage_capacity_by_product_id, 15.0, 30.0)

    disk_item = next(i for i in result if i["product_id"] == 2)
    assert disk_item["quantity"] == 8


def test_calculate_storage_never_reduces_existing_quantity():
    items = [
        {"product_id": 1, "description": "Cámara IP 4MP", "quantity": 1},
        {"product_id": 2, "description": "Disco duro 2TB", "quantity": 10},  # el técnico ya pidió de más
    ]
    resolution_by_product_id = {1: 4.0}
    storage_capacity_by_product_id = {2: 2000.0}

    result = calculate_storage(items, resolution_by_product_id, storage_capacity_by_product_id, 15.0, 30.0)

    disk_item = next(i for i in result if i["product_id"] == 2)
    assert disk_item["quantity"] == 10  # no se le baja, aunque la matemática pida menos


def test_calculate_storage_does_nothing_without_cameras():
    items = [{"product_id": 2, "description": "Disco duro 2TB", "quantity": 1}]

    result = calculate_storage(items, {}, {2: 2000.0}, 15.0, 30.0)

    assert result == items


def test_calculate_storage_does_not_add_a_disk_line_when_none_exists():
    items = [{"product_id": 1, "description": "Cámara IP 4MP", "quantity": 8}]
    resolution_by_product_id = {1: 4.0}

    result = calculate_storage(items, resolution_by_product_id, {}, 15.0, 30.0)

    assert result == items  # ningún producto de almacenamiento en el presupuesto -> nada que ajustar


CAPACITY_CATALOG = [
    {"id": 1, "name": "Cámara IP", "tags": ["camara"]},
    {"id": 2, "name": "NVR 8 canales", "tags": ["nvr"]},
    {"id": 3, "name": "Switch PoE 8 puertos", "tags": ["poe-switch"]},
]


def test_calculate_capacity_warns_when_nvr_channels_are_insufficient():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 12},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 1},
    ]
    capacity_by_product_id = {2: 8}

    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, capacity_by_product_id)

    assert len(warnings) == 1
    assert "NVR" in warnings[0]
    assert "faltan 4" in warnings[0]


def test_calculate_capacity_no_warning_when_nvr_channels_are_sufficient():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 8},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 1},
    ]
    capacity_by_product_id = {2: 8}

    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, capacity_by_product_id)

    assert warnings == []


def test_calculate_capacity_accounts_for_multiple_nvr_units():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 16},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 2},
    ]
    capacity_by_product_id = {2: 8}

    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, capacity_by_product_id)

    assert warnings == []  # 2 NVR x 8 canales = 16, alcanza exacto


def test_calculate_capacity_warns_separately_for_switch_ports():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 12},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 2},  # alcanza (16 >= 12)
        {"product_id": 3, "description": "Switch PoE 8 puertos", "quantity": 1},  # no alcanza (8 < 12)
    ]
    capacity_by_product_id = {2: 8, 3: 8}

    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, capacity_by_product_id)

    assert len(warnings) == 1
    assert "Switch PoE" in warnings[0]


def test_calculate_capacity_skips_check_when_capacity_unknown():
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 12},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 1},
    ]

    # sin channel_capacity cargado para el NVR -> no se puede comparar, no se advierte
    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, {})

    assert warnings == []


def test_calculate_capacity_no_warning_without_any_hub_in_budget():
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 12}]

    warnings = calculate_capacity_warnings(items, CAPACITY_CATALOG, {2: 8, 3: 8})

    assert warnings == []
