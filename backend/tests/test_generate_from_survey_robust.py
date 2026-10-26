from unittest.mock import patch

from fastapi import HTTPException

from tests.conftest import auth_headers, make_project
from tests.test_generate_from_survey import _create_product


def test_a_zero_quantity_line_is_skipped_with_a_warning_instead_of_crashing(client, admin_token):
    """Regresión: la IA dio una línea con cantidad 0 y la generación entera fallaba con un error interno."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    good = _create_product(client, headers)
    bad = _create_product(client, headers, name="Cámara bullet")

    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[
                {"product_id": good["id"], "description": good["name"], "quantity": 4},
                {"product_id": bad["id"], "description": bad["name"], "quantity": 0},
            ],
        ),
        patch("app.ai_engine.documents.draft_engineering", side_effect=HTTPException(status_code=502, detail="x")),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [i["quantity"] for i in body["budget"]["items"]] == [4]
    assert any("Cámara bullet" in w and "omitió" in w for w in body["warnings"])


def test_when_no_line_is_valid_the_answer_explains_it(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    only = _create_product(client, headers)
    with (
        patch(
            "app.ai_engine.documents.suggest_budget_items",
            return_value=[{"product_id": only["id"], "description": only["name"], "quantity": 0}],
        ),
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(f"/api/projects/{project['id']}/generate-from-survey", headers=headers)
    assert resp.status_code == 400
    assert "ninguna línea válida" in resp.json()["detail"]
