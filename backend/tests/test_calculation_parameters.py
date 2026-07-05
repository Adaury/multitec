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
