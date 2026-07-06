from unittest.mock import patch

from tests.conftest import auth_headers, make_category, make_project


def _create_product(client, headers, category_id=None, **overrides):
    if category_id is None:
        category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Cámara IP", "unit": "unidad", "price": 150}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_create_add_accessory_rule(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)

    resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={"action_type": "add_accessory", "target_tag": "nvr", "per_source_units": 8, "quantity": 1},
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["action_type"] == "add_accessory"
    assert body["target_tag"] == "nvr"
    assert body["per_source_units"] == 8
    assert body["quantity"] == 1


def test_create_technical_rule_rejects_unknown_action_type(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)

    resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={"action_type": "totally_made_up_type", "target_tag": "nvr"},
        headers=headers,
    )

    assert resp.status_code == 422  # ningún miembro de la unión discriminada matchea


def test_create_set_calculation_parameter_rule(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers, name="Fibra monomodo")

    resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={
            "action_type": "set_calculation_parameter",
            "parameter_key": "cable_waste_margin_pct",
            "value": 0.08,
        },
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["action_type"] == "set_calculation_parameter"
    assert body["parameter_key"] == "cable_waste_margin_pct"
    assert body["value"] == 0.08
    assert body["target_tag"] is None  # no aplica a este action_type


def test_create_set_calculation_parameter_rule_rejects_unknown_parameter(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)

    resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={"action_type": "set_calculation_parameter", "parameter_key": "no_existe", "value": 1},
        headers=headers,
    )

    assert resp.status_code == 400


def test_create_flag_engineering_note_rule(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers, name="Fibra monomodo")

    resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={
            "action_type": "flag_engineering_note",
            "engineering_note": "Verificar distancia máxima de fibra monomodo.",
        },
        headers=headers,
    )

    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["action_type"] == "flag_engineering_note"
    assert body["engineering_note"] == "Verificar distancia máxima de fibra monomodo."
    assert body["quantity"] == 1  # default no aplicable, sin efecto para este action_type


def test_update_technical_rule_changes_quantity(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    create_resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={"action_type": "add_accessory", "target_tag": "nvr", "quantity": 1},
        headers=headers,
    )
    rule_id = create_resp.json()["id"]

    resp = client.put(f"/api/catalog/technical-rules/{rule_id}", json={"quantity": 3}, headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["quantity"] == 3
    assert body["target_tag"] == "nvr"  # no se pierde al actualizar solo la cantidad


def test_delete_technical_rule(client, admin_token):
    headers = auth_headers(admin_token)
    product = _create_product(client, headers)
    create_resp = client.post(
        f"/api/catalog/{product['id']}/technical-rules",
        json={"action_type": "add_accessory", "target_tag": "nvr"},
        headers=headers,
    )
    rule_id = create_resp.json()["id"]

    resp = client.delete(f"/api/catalog/technical-rules/{rule_id}", headers=headers)
    assert resp.status_code == 204

    list_resp = client.get(f"/api/catalog/{product['id']}/technical-rules", headers=headers)
    assert list_resp.json() == []


def test_technical_rule_expands_alongside_catalog_rule_in_generate_from_survey(client, admin_token):
    """§ Fase 2: una TechnicalRule (mecanismo nuevo) y una CatalogRule (mecanismo
    original) deben poder convivir y aplicarse juntas en la misma generación."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    nvr_category = make_category(client, headers, name="NVR", code_prefix="NVR")["id"]
    switch_category = make_category(client, headers, name="Switch", code_prefix="SW")["id"]
    camera = _create_product(client, headers, category_id=camera_category, name="Cámara IP")
    nvr = _create_product(client, headers, category_id=nvr_category, name="NVR 8 canales", price=400, tags=["nvr"])
    switch = _create_product(
        client, headers, category_id=switch_category, name="Switch PoE 8p", price=200, tags=["poe-switch"]
    )

    # Regla original (CatalogRule): 1 NVR fijo si hay cámaras.
    rule_resp = client.post(
        f"/api/catalog/{camera['id']}/rules",
        json={"target_tag": "nvr", "per_source_units": None, "quantity": 1},
        headers=headers,
    )
    assert rule_resp.status_code == 201, rule_resp.text

    # Regla nueva (TechnicalRule): 1 switch PoE cada 8 cámaras.
    tech_rule_resp = client.post(
        f"/api/catalog/{camera['id']}/technical-rules",
        json={"action_type": "add_accessory", "target_tag": "poe-switch", "per_source_units": 8, "quantity": 1},
        headers=headers,
    )
    assert tech_rule_resp.status_code == 201, tech_rule_resp.text

    engineering_draft = {
        "recommended_equipment": "8 cámaras IP",
        "distribution": "Perímetro",
        "conduits": "PVC 3/4",
        "wiring": "UTP cat6",
        "technical_design": "NVR central con PoE",
        "observations": "Ninguna",
    }
    with (
        patch(
            "app.api.routers.ai.suggest_budget_items",
            return_value=[{"product_id": camera["id"], "description": camera["name"], "quantity": 8}],
        ),
        patch("app.api.routers.ai.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    items_by_product = {item["product_id"]: item for item in resp.json()["quote"]["items"]}
    assert items_by_product[nvr["id"]]["quantity"] == 1  # vía CatalogRule
    assert items_by_product[switch["id"]]["quantity"] == 1  # vía TechnicalRule


def test_set_calculation_parameter_and_flag_engineering_note_apply_in_generate_from_survey(client, admin_token):
    """Motor 4 -> Motor 5/6: una regla set_calculation_parameter sube el margen de
    desperdicio de cable solo porque hay fibra en el presupuesto, y una regla
    flag_engineering_note agrega su nota al borrador de ingeniería — ambas activadas por
    la presencia del mismo producto "fibra", sin tocar el default global ni pisar el
    borrador que la IA generó."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    fiber_category = make_category(client, headers, name="Fibra óptica", code_prefix="FIB")["id"]
    fiber = _create_product(
        client, headers, category_id=fiber_category, name="Fibra monomodo", unit="metro", tags=["cable"]
    )

    param_rule = client.post(
        f"/api/catalog/{fiber['id']}/technical-rules",
        json={"action_type": "set_calculation_parameter", "parameter_key": "cable_waste_margin_pct", "value": 0.2},
        headers=headers,
    )
    assert param_rule.status_code == 201, param_rule.text

    note_rule = client.post(
        f"/api/catalog/{fiber['id']}/technical-rules",
        json={
            "action_type": "flag_engineering_note",
            "engineering_note": "Verificar distancia máxima de fibra monomodo.",
        },
        headers=headers,
    )
    assert note_rule.status_code == 201, note_rule.text

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "Instalación estándar.",
    }
    with (
        patch(
            "app.api.routers.ai.suggest_budget_items",
            return_value=[{"product_id": fiber["id"], "description": fiber["name"], "quantity": 100}],
        ),
        patch("app.api.routers.ai.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    items_by_product = {item["product_id"]: item for item in resp.json()["quote"]["items"]}
    # 100 * 1.20 (override 20%, no el default 5%) = 120
    assert items_by_product[fiber["id"]]["quantity"] == 120

    engineering = client.get(f"/api/projects/{project['id']}/engineering", headers=headers).json()
    assert "Instalación estándar." in engineering["observations"]
    assert "Verificar distancia máxima de fibra monomodo." in engineering["observations"]
