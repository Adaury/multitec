from unittest.mock import patch

from tests.conftest import auth_headers, make_project


def test_ask_single_project_uses_mocked_ai(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    with (
        patch("app.api.routers.ai.answer_question", return_value="Respuesta simulada") as mocked_answer,
        patch("app.api.routers.ai.reindex_project"),
    ):
        resp = client.post(
            "/api/ai/ask",
            json={"project_id": project["id"], "question": "¿Cuál es el estado?"},
            headers=headers,
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Respuesta simulada"
    assert body["projects"] == [project["code"]]
    mocked_answer.assert_called_once()


def test_ask_unknown_project_404(client, admin_token):
    headers = auth_headers(admin_token)
    resp = client.post("/api/ai/ask", json={"project_id": 999999, "question": "hola"}, headers=headers)
    assert resp.status_code == 404


def test_ask_all_projects_without_index_returns_friendly_message(client, admin_token):
    headers = auth_headers(admin_token)
    make_project(client, headers)  # existe un proyecto, pero nunca se indexó

    resp = client.post("/api/ai/ask", json={"question": "¿Algo?"}, headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["projects"] == []
    assert "indexados" in body["answer"]


def test_ask_all_projects_uses_search_and_combines_context(client, admin_token, db_session):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)

    # Se busca el proyecto real (session-attached) para que _build_project_context
    # pueda resolver project.client sin necesitar una sesión propia.
    from app.models.project import Project

    real_project = db_session.get(Project, project["id"])

    with (
        patch("app.api.routers.ai.search_projects", return_value=[real_project]) as mocked_search,
        patch("app.api.routers.ai.answer_question", return_value="Respuesta combinada") as mocked_answer,
    ):
        resp = client.post("/api/ai/ask", json={"question": "¿Qué proyectos hay?"}, headers=headers)

    assert resp.status_code == 200
    body = resp.json()
    assert body["projects"] == [project["code"]]
    assert body["answer"] == "Respuesta combinada"
    mocked_answer.assert_called_once()
    mocked_search.assert_called_once()
