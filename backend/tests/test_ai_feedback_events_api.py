from unittest.mock import patch

from fastapi import HTTPException

from tests.conftest import auth_headers, make_project


def _create_product(client, headers, **overrides):
    from tests.conftest import make_category

    category_id = make_category(client, headers)["id"]
    payload = {"category_id": category_id, "name": "Cámara IP", "unit": "unidad", "price": 150}
    payload.update(overrides)
    resp = client.post("/api/catalog", json=payload, headers=headers)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_generate_from_survey_marks_budget_and_engineering_as_ai_generated(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers)

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
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": camera["id"], "description": camera["name"], "quantity": 8}],
        ),
        patch("app.ai_engine.documents.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["budget"]["ai_generated"] is True

    engineering = client.get(f"/api/projects/{project['id']}/engineering", headers=headers).json()
    assert engineering["ai_generated"] is True


def test_editing_ai_generated_budget_records_feedback_and_clears_flag(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers)

    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": camera["id"], "description": camera["name"], "quantity": 8}],
        ),
        patch(
            "app.ai_engine.documents.draft_engineering",
            side_effect=HTTPException(status_code=400, detail="Ollama no disponible"),
        ),
        patch("app.api.routers.ai.reindex_project"),
    ):
        gen_resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)
    assert gen_resp.status_code == 200, gen_resp.text
    budget = gen_resp.json()["budget"]
    assert budget["ai_generated"] is True

    update_resp = client.put(
        f"/api/budgets/{budget['id']}",
        json={"items": [{"product_id": camera["id"], "description": camera["name"], "quantity": 12, "unit_price": 150}]},
        headers=headers,
    )
    assert update_resp.status_code == 200, update_resp.text
    assert update_resp.json()["ai_generated"] is False

    events = client.get(f"/api/ai-feedback-events?project_id={project['id']}", headers=headers).json()
    assert len(events) == 1
    assert events[0]["entity_type"] == "budget_item"
    assert events[0]["origin"] == "human_modified"
    assert events[0]["field_changed"] == "quantity"
    assert events[0]["old_value"] == "8.0"
    assert events[0]["new_value"] == "12.0"

    # Segunda edición: ya no hay "sugerencia de IA" con la cual contrastar, no debe
    # generar un evento nuevo.
    client.put(
        f"/api/budgets/{budget['id']}",
        json={"items": [{"product_id": camera["id"], "description": camera["name"], "quantity": 999, "unit_price": 150}]},
        headers=headers,
    )
    events_after = client.get(f"/api/ai-feedback-events?project_id={project['id']}", headers=headers).json()
    assert len(events_after) == 1


def test_manually_created_budget_edit_records_no_feedback(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    budget = client.post(
        f"/api/projects/{project['id']}/budgets",
        json={"items": [{"description": "Cable UTP", "quantity": 100, "unit_price": 2}]},
        headers=headers,
    ).json()
    assert budget["ai_generated"] is False

    client.put(
        f"/api/budgets/{budget['id']}",
        json={"items": [{"description": "Cable UTP", "quantity": 300, "unit_price": 2}]},
        headers=headers,
    )

    events = client.get(f"/api/ai-feedback-events?project_id={project['id']}", headers=headers).json()
    assert events == []


def test_editing_ai_generated_engineering_records_feedback(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    camera = _create_product(client, headers)

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
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": camera["id"], "description": camera["name"], "quantity": 8}],
        ),
        patch("app.ai_engine.documents.draft_engineering", return_value=engineering_draft),
        patch("app.api.routers.ai.reindex_project"),
    ):
        client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    put_resp = client.put(
        f"/api/projects/{project['id']}/engineering",
        json={**engineering_draft, "distribution": "Perímetro + interior"},
        headers=headers,
    )
    assert put_resp.status_code == 200, put_resp.text
    assert put_resp.json()["ai_generated"] is False

    events = client.get(f"/api/ai-feedback-events?project_id={project['id']}", headers=headers).json()
    assert len(events) == 1
    assert events[0]["entity_type"] == "engineering"
    assert events[0]["field_changed"] == "distribution"
    assert events[0]["old_value"] == "Perímetro"
    assert events[0]["new_value"] == "Perímetro + interior"
