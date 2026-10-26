"""La generación con IA corre en el servidor: se arranca, se consulta y sobrevive a que la pantalla se cierre."""

import threading
import time
from unittest.mock import patch

from tests.conftest import assign_to_tecnico, auth_headers, make_category, make_project

ENGINEERING = {
    key: "x"
    for key in ("recommended_equipment", "distribution", "conduits", "wiring", "technical_design", "observations")
}


def _product(client, headers):
    category = make_category(client, headers)["id"]
    resp = client.post(
        "/api/catalog",
        json={"category_id": category, "name": "Cámara domo IP 4MP", "unit": "unidad", "price": 150},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _wait(client, headers, project_id, timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = client.get(f"/api/projects/{project_id}/generate-from-survey/status", headers=headers).json()
        if body["status"] != "running":
            return body
        time.sleep(0.1)
    raise AssertionError("la generación no terminó a tiempo")


def _suggest(product, quantity=8):
    return patch(
        "app.ai_engine.documents.suggest_budget_items",
        return_value=[{"product_id": product["id"], "description": product["name"], "quantity": quantity}],
    )


def test_generation_runs_in_the_background_and_can_be_polled(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers, client_name="Hotel Costa Azul")
    product = _product(client, headers)

    status_url = f"/api/projects/{project['id']}/generate-from-survey/status"
    assert client.get(status_url, headers=headers).json()["status"] == "none"

    with (
        _suggest(product),
        patch("app.ai_engine.documents.draft_engineering", return_value=ENGINEERING),
        patch("app.api.routers.ai.reindex_project"),
    ):
        started = client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers)
        assert started.status_code == 202, started.text
        assert started.json()["label"] == "Hotel Costa Azul"
        done = _wait(client, headers, project["id"])

    assert done["status"] == "done", done
    assert done["result"]["quote"]["status"] == "pendiente"
    assert done["result"]["budget"]["items"][0]["quantity"] == 8
    assert len(client.get(f"/api/projects/{project['id']}/quotes", headers=headers).json()) == 1


def test_starting_twice_joins_the_running_job_and_does_not_duplicate_the_quote(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers)
    release = threading.Event()

    def slow_suggest(*args, **kwargs):
        release.wait(5)
        return [{"product_id": product["id"], "description": product["name"], "quantity": 2}]

    with (
        patch("app.ai_engine.documents.suggest_budget_items", side_effect=slow_suggest),
        patch("app.ai_engine.documents.draft_engineering", return_value=ENGINEERING),
        patch("app.api.routers.ai.reindex_project"),
    ):
        first = client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers).json()
        second = client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers).json()
        assert first["status"] == "running" and second["status"] == "running"
        assert first["started_at"] == second["started_at"]  # es el mismo trabajo
        release.set()
        done = _wait(client, headers, project["id"])

    assert done["status"] == "done"
    assert len(client.get(f"/api/projects/{project['id']}/quotes", headers=headers).json()) == 1


def test_a_failed_generation_reports_a_readable_error_and_can_be_retried(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers)

    with (
        patch("app.ai_engine.documents.suggest_budget_items", side_effect=RuntimeError("Ollama no responde")),
        patch("app.api.routers.ai.reindex_project"),
    ):
        client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers)
        failed = _wait(client, headers, project["id"])
    assert failed["status"] == "error"
    assert "intenta de nuevo" in failed["error"] and "Ollama" not in failed["error"]  # nada interno al usuario

    with (
        _suggest(product),
        patch("app.ai_engine.documents.draft_engineering", return_value=ENGINEERING),
        patch("app.api.routers.ai.reindex_project"),
    ):
        client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers)
        assert _wait(client, headers, project["id"])["status"] == "done"


def test_my_jobs_list_lets_the_app_recover_after_being_closed(client, admin_token, oficina_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    product = _product(client, headers)
    with (
        _suggest(product),
        patch("app.ai_engine.documents.draft_engineering", return_value=ENGINEERING),
        patch("app.api.routers.ai.reindex_project"),
    ):
        client.post(f"/api/projects/{project['id']}/generate-from-survey/start", headers=headers)
        _wait(client, headers, project["id"])

    mine = client.get("/api/ai/generation-jobs", headers=headers).json()
    assert [j["project_id"] for j in mine] == [project["id"]] and mine[0]["status"] == "done"
    # Cada quien ve solo sus trabajos.
    assert client.get("/api/ai/generation-jobs", headers=auth_headers(oficina_token)).json() == []


def test_a_technician_cannot_start_or_read_a_generation_of_a_project_that_is_not_theirs(
    client, admin_token, tecnico_token, db_session
):
    admin = auth_headers(admin_token)
    tec = auth_headers(tecnico_token)
    foreign = make_project(client, admin)
    assert client.post(f"/api/projects/{foreign['id']}/generate-from-survey/start", headers=tec).status_code == 404
    assert client.get(f"/api/projects/{foreign['id']}/generate-from-survey/status", headers=tec).status_code == 404

    mine = make_project(client, admin)
    assign_to_tecnico(db_session, mine)
    assert client.get(f"/api/projects/{mine['id']}/generate-from-survey/status", headers=tec).status_code == 200
