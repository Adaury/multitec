from unittest.mock import patch

from fastapi import HTTPException

from tests.conftest import auth_headers, make_category, make_project


def _create_product(client, headers, category_id=None, **overrides):
    if category_id is None:
        category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Cámara domo IP 4MP", "unit": "unidad", "price": 150}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_generate_from_survey_creates_budget_and_pending_quote(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _create_product(client, headers)

    engineering_draft = {
        "recommended_equipment": "8 cámaras domo IP",
        "distribution": "Perímetro del edificio",
        "conduits": "PVC 3/4",
        "wiring": "UTP cat6",
        "technical_design": "NVR central con PoE",
        "observations": "Ninguna",
    }

    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": product["id"], "description": product["name"], "quantity": 8}],
        ) as mocked_suggest,
        patch("app.ai_engine.documents.draft_engineering", return_value=engineering_draft) as mocked_draft,
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["budget"]["items"][0]["quantity"] == 8
    assert body["quote"]["status"] == "pendiente"
    assert body["quote"]["items"][0]["product_id"] == product["id"]
    assert body["quote"]["items"][0]["unit_price"] == 150  # inyectado desde el catálogo real
    assert body["engineering_drafted"] is True
    mocked_suggest.assert_called_once()
    mocked_draft.assert_called_once()

    # No se auto-aprueba: no debe haber materiales todavía (solo se generan al aprobar).
    materials = client.get(f"/api/projects/{project['id']}/materials", headers=headers).json()
    assert materials == []

    # La ingeniería sí quedó rellena en el proyecto.
    engineering = client.get(f"/api/projects/{project['id']}/engineering", headers=headers).json()
    assert engineering["recommended_equipment"] == "8 cámaras domo IP"


def test_generate_from_survey_expands_rules_with_quantity(client, admin_token):
    """§ catálogo inteligente v2: las reglas con cantidad (no solo presencia) agregan
    accesorios en la proporción correcta — sin que la IA tenga que hacer esa aritmética."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera_category = make_category(client, headers, name="Cámaras IP", code_prefix="CAM")["id"]
    nvr_category = make_category(client, headers, name="NVR", code_prefix="NVR")["id"]
    camera = _create_product(client, headers, category_id=camera_category, name="Cámara IP")
    nvr = _create_product(client, headers, category_id=nvr_category, name="NVR 8 canales", price=400, tags=["nvr"])

    rule_resp = client.post(
        f"/api/catalog/{camera['id']}/rules",
        json={"target_tag": "nvr", "per_source_units": 8, "quantity": 1},
        headers=headers,
    )
    assert rule_resp.status_code == 201, rule_resp.text

    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": camera["id"], "description": camera["name"], "quantity": 9}],
        ),
        patch(
            "app.ai_engine.documents.draft_engineering",
            side_effect=HTTPException(status_code=400, detail="Ollama no disponible"),
        ),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    items_by_product = {item["product_id"]: item for item in body["quote"]["items"]}
    assert items_by_product[camera["id"]]["quantity"] == 9
    # 9 cámaras, 1 NVR cada 8 -> ceil(9/8) = 2 lotes, sin que la IA lo haya calculado.
    assert items_by_product[nvr["id"]]["quantity"] == 2
    # draft_engineering falló (no HTTPException, un error genérico) — no debe tumbar la
    # respuesta ni la cotización ya generada.
    assert body["engineering_drafted"] is False


def test_generate_from_survey_requires_at_least_one_item(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    with (
        patch("app.ai_engine.documents.suggest_budget_items", return_value=[]),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 400


def test_generate_from_survey_does_not_overwrite_existing_engineering(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _create_product(client, headers)

    put_resp = client.put(
        f"/api/projects/{project['id']}/engineering",
        json={
            "recommended_equipment": "Ya definido a mano",
            "distribution": "-",
            "conduits": "-",
            "wiring": "-",
            "technical_design": "-",
            "observations": "-",
        },
        headers=headers,
    )
    assert put_resp.status_code == 200, put_resp.text

    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": product["id"], "description": product["name"], "quantity": 1}],
        ),
        patch("app.ai_engine.documents.draft_engineering") as mocked_draft,
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    assert resp.json()["engineering_drafted"] is False
    mocked_draft.assert_not_called()

    engineering = client.get(f"/api/projects/{project['id']}/engineering", headers=headers).json()
    assert engineering["recommended_equipment"] == "Ya definido a mano"
