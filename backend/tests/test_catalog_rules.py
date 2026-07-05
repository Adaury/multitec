from app.ai_engine.rules import expand_with_rules

CATALOG = [
    {"id": 1, "name": "Cámara IP", "tags": ["camara", "ip"]},
    {"id": 2, "name": "NVR 8 canales", "tags": ["nvr"]},
    {"id": 3, "name": "Switch PoE 8 puertos", "tags": ["poe-switch"]},
    {"id": 4, "name": "Disco duro 2TB", "tags": ["disco-duro"]},
    {"id": 5, "name": "Conector RJ45", "tags": ["conector"]},
]


def test_fixed_mode_adds_quantity_once_regardless_of_source_quantity():
    rules = [{"source_product_id": 1, "target_tag": "nvr", "per_source_units": None, "quantity": 1}]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 12}]

    result = expand_with_rules(items, CATALOG, rules)

    nvr_item = next(i for i in result if i["product_id"] == 2)
    assert nvr_item["quantity"] == 1


def test_proportional_mode_exact_multiple():
    rules = [{"source_product_id": 1, "target_tag": "poe-switch", "per_source_units": 8, "quantity": 1}]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 8}]

    result = expand_with_rules(items, CATALOG, rules)

    switch_item = next(i for i in result if i["product_id"] == 3)
    assert switch_item["quantity"] == 1


def test_proportional_mode_rounds_up():
    rules = [{"source_product_id": 1, "target_tag": "disco-duro", "per_source_units": 4, "quantity": 1}]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 9}]

    result = expand_with_rules(items, CATALOG, rules)

    disk_item = next(i for i in result if i["product_id"] == 4)
    assert disk_item["quantity"] == 3  # ceil(9/4) = 3 lotes


def test_multiple_rules_on_same_source_all_apply():
    rules = [
        {"source_product_id": 1, "target_tag": "nvr", "per_source_units": None, "quantity": 1},
        {"source_product_id": 1, "target_tag": "poe-switch", "per_source_units": 8, "quantity": 1},
    ]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 8}]

    result = expand_with_rules(items, CATALOG, rules)
    product_ids = {i["product_id"] for i in result}

    assert 2 in product_ids  # NVR
    assert 3 in product_ids  # switch


def test_rules_from_different_sources_targeting_same_accessory_sum_up():
    # Cámara y algo más, ambas apuntando a "conector" con cantidad fija — deben sumarse.
    rules = [
        {"source_product_id": 1, "target_tag": "conector", "per_source_units": None, "quantity": 2},
    ]
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 1},
    ]
    result = expand_with_rules(items, CATALOG, rules)
    connector_item = next(i for i in result if i["product_id"] == 5)
    assert connector_item["quantity"] == 2


def test_no_matching_accessory_in_catalog_adds_nothing():
    rules = [{"source_product_id": 1, "target_tag": "caja-terminacion", "per_source_units": None, "quantity": 1}]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 1}]

    result = expand_with_rules(items, CATALOG, rules)

    assert len(result) == 1  # nada se agregó, ningún producto del catálogo tiene ese tag


def test_explicitly_mentioned_accessory_is_not_duplicated():
    rules = [{"source_product_id": 1, "target_tag": "nvr", "per_source_units": None, "quantity": 1}]
    items = [
        {"product_id": 1, "description": "Cámara IP", "quantity": 4},
        {"product_id": 2, "description": "NVR 8 canales", "quantity": 1},  # el técnico ya lo mencionó
    ]

    result = expand_with_rules(items, CATALOG, rules)

    nvr_items = [i for i in result if i["product_id"] == 2]
    assert len(nvr_items) == 1
    assert nvr_items[0]["quantity"] == 1  # no se le suma la regla encima


def test_zero_quantity_source_does_not_trigger_proportional_rule():
    rules = [{"source_product_id": 1, "target_tag": "nvr", "per_source_units": 8, "quantity": 1}]
    items = [{"product_id": 1, "description": "Cámara IP", "quantity": 0}]

    result = expand_with_rules(items, CATALOG, rules)

    assert len(result) == 1
