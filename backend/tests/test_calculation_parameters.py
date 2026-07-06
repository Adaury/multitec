from unittest.mock import patch

from tests.conftest import auth_headers, make_category, make_project


def test_list_shows_default_when_unconfigured(client, admin_token):
    headers = auth_headers(admin_token)

    resp = client.get("/api/calculation-parameters", headers=headers)

    assert resp.status_code == 200, resp.text
    params = {p["key"]: p for p in resp.json()}
    assert params["cable_waste_margin_pct"]["value"] == 0.05
    assert params["cable_waste_margin_pct"]["is_default"] is True


def test_upsert_overrides_default(client, admin_token):
    headers = auth_headers(admin_token)

    resp = client.put("/api/calculation-parameters/cable_waste_margin_pct", json={"value": 0.1}, headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["value"] == 0.1
    assert resp.json()["is_default"] is False

    list_resp = client.get("/api/calculation-parameters", headers=headers)
    params = {p["key"]: p for p in list_resp.json()}
    assert params["cable_waste_margin_pct"]["value"] == 0.1
    assert params["cable_waste_margin_pct"]["is_default"] is False


def test_upsert_unknown_key_404(client, admin_token):
    headers = auth_headers(admin_token)

    resp = client.put("/api/calculation-parameters/not_a_real_key", json={"value": 1}, headers=headers)

    assert resp.status_code == 404


def _create_product(client, headers, category_id=None, **overrides):
    if category_id is None:
        category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Cable UTP Cat6", "unit": "metro", "price": 2, "tags": ["cable"]}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_generate_from_survey_applies_configured_cable_waste_margin(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    cable = _create_product(client, headers)

    put_resp = client.put("/api/calculation-parameters/cable_waste_margin_pct", json={"value": 0.1}, headers=headers)
    assert put_resp.status_code == 200, put_resp.text

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "-",
    }
    with (
        patch(
            "app.api.routers.ai.suggest_budget_items",
            return_value=[{"product_id": cable["id"], "description": cable["name"], "quantity": 200}],
        ),
        patch("app.api.routers.ai.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    items_by_product = {item["product_id"]: item for item in resp.json()["quote"]["items"]}
    assert items_by_product[cable["id"]]["quantity"] == 220  # 200 * 1.1


def test_generate_from_survey_adds_estimated_labor_line(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    camera = _create_product(
        client, headers, category_id=camera_category, name="Cámara IP", unit="unidad", tags=[],
        install_minutes=30, labor_role="técnico CCTV",
    )

    client.put("/api/calculation-parameters/labor_hourly_rate", json={"value": 100}, headers=headers)

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "-",
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
    labor_items = [item for item in resp.json()["quote"]["items"] if item["product_id"] is None]
    assert len(labor_items) == 1
    # 8 cámaras * 30 min = 240 min = 4 horas * RD$100/h = RD$400
    assert labor_items[0]["quantity"] == 4.0
    assert labor_items[0]["unit_price"] == 100.0
    assert "Mano de obra de instalación" in labor_items[0]["description"]


def test_generate_from_survey_has_no_labor_line_without_install_minutes(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers, name="Cámara IP", unit="unidad", tags=[])  # sin install_minutes

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "-",
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
    labor_items = [item for item in resp.json()["quote"]["items"] if item["product_id"] is None]
    assert labor_items == []


def test_generate_from_survey_bumps_disk_quantity_to_meet_storage_needs(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    disk_category = make_category(client, headers, name="Almacenamiento", code_prefix="DIS")["id"]
    camera = _create_product(
        client, headers, category_id=camera_category, name="Cámara IP 2MP", unit="unidad", tags=[],
        resolution_mp=2,
    )
    disk = _create_product(
        client, headers, category_id=disk_category, name="Disco duro 10GB", unit="unidad", tags=[],
        storage_capacity_gb=10,
    )

    client.put(
        "/api/calculation-parameters/storage_gb_per_megapixel_per_day", json={"value": 1}, headers=headers
    )
    client.put("/api/calculation-parameters/storage_retention_days", json={"value": 10}, headers=headers)

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "-",
    }
    with (
        patch(
            "app.api.routers.ai.suggest_budget_items",
            return_value=[
                {"product_id": camera["id"], "description": camera["name"], "quantity": 5},
                {"product_id": disk["id"], "description": disk["name"], "quantity": 1},
            ],
        ),
        patch("app.api.routers.ai.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    items_by_product = {item["product_id"]: item for item in resp.json()["quote"]["items"]}
    # 5 cámaras * 2MP * 1 GB/MP/día * 10 días = 100 GB -> ceil(100/10) = 10 discos
    assert items_by_product[disk["id"]]["quantity"] == 10


def test_generate_from_survey_warns_when_nvr_capacity_is_insufficient(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    nvr_category = make_category(client, headers, name="NVR", code_prefix="NVR")["id"]
    camera = _create_product(
        client, headers, category_id=camera_category, name="Cámara IP", unit="unidad", tags=["camara"],
    )
    nvr = _create_product(
        client, headers, category_id=nvr_category, name="NVR 8 canales", unit="unidad", tags=["nvr"],
        channel_capacity=8,
    )

    engineering_draft = {
        "recommended_equipment": "-",
        "distribution": "-",
        "conduits": "-",
        "wiring": "-",
        "technical_design": "-",
        "observations": "-",
    }
    with (
        patch(
            "app.api.routers.ai.suggest_budget_items",
            return_value=[
                {"product_id": camera["id"], "description": camera["name"], "quantity": 12},
                {"product_id": nvr["id"], "description": nvr["name"], "quantity": 1},
            ],
        ),
        patch("app.api.routers.ai.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    warnings = resp.json()["warnings"]
    assert len(warnings) == 1
    assert "NVR" in warnings[0]
    assert "faltan 4" in warnings[0]

    # el presupuesto se genera igual, con la cantidad que el técnico/IA pidió — la
    # advertencia no bloquea ni corrige nada por su cuenta
    items_by_product = {item["product_id"]: item for item in resp.json()["quote"]["items"]}
    assert items_by_product[nvr["id"]]["quantity"] == 1
