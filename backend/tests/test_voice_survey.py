import io
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.ai_engine.nlu import classify_voice_transcript
from tests.conftest import auth_headers, make_project


def _upload_audio(client, headers, project_id, content_type="audio/webm;codecs=opus"):
    files = {"file": ("nota-voz.webm", io.BytesIO(b"fake-audio-bytes"), content_type)}
    return client.post(
        f"/api/projects/{project_id}/survey/assets", data={"kind": "audio"}, files=files, headers=headers
    )


def test_audio_upload_accepts_codecs_parameter(client, admin_token):
    """Chrome etiqueta las grabaciones 'audio/webm;codecs=opus' — antes se rechazaban con 400."""
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    resp = _upload_audio(client, headers, project["id"])
    assert resp.status_code == 201, resp.text
    assert resp.json()["kind"] == "audio"


def test_audio_upload_still_rejects_other_types(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    resp = _upload_audio(client, headers, project["id"], content_type="application/pdf")
    assert resp.status_code == 400


def test_transcribe_returns_transcript_and_fields(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    asset = _upload_audio(client, headers, project["id"]).json()

    fields = {"notes": "Instalar 4 cámaras", "measurements": "20 metros de cable", "observations": "", "classified": True}
    with (
        patch("app.api.routers.ai.transcribe_audio", return_value="instalar cuatro cámaras y veinte metros de cable"),
        patch("app.api.routers.ai.classify_voice_transcript", return_value=fields),
    ):
        resp = client.post(
            f"/api/projects/{project['id']}/survey/assets/{asset['id']}/transcribe", headers=headers
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["transcript"].startswith("instalar cuatro")
    assert body["notes"] == "Instalar 4 cámaras"
    assert body["measurements"] == "20 metros de cable"
    assert body["classified"] is True

    # el texto queda como descripción del audio y el Survey no se modifica solo
    survey = client.get(f"/api/projects/{project['id']}/survey", headers=headers).json()
    assert survey["assets"][0]["description"].startswith("instalar cuatro")
    assert not survey["notes"]


def test_transcribe_empty_audio_is_422(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    asset = _upload_audio(client, headers, project["id"]).json()
    with patch("app.api.routers.ai.transcribe_audio", return_value=""):
        resp = client.post(
            f"/api/projects/{project['id']}/survey/assets/{asset['id']}/transcribe", headers=headers
        )
    assert resp.status_code == 422


def test_transcribe_unknown_or_non_audio_asset_404(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    photo = client.post(
        f"/api/projects/{project['id']}/survey/assets",
        data={"kind": "photo"},
        files={"file": ("f.png", io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"0" * 20), "image/png")},
        headers=headers,
    ).json()
    for asset_id in (999999, photo["id"]):
        resp = client.post(f"/api/projects/{project['id']}/survey/assets/{asset_id}/transcribe", headers=headers)
        assert resp.status_code == 404


def test_transcribe_requires_auth(client):
    assert client.post("/api/projects/1/survey/assets/1/transcribe").status_code == 401


def _fake_ollama(content):
    class Client:
        def chat(self, **kwargs):
            return SimpleNamespace(message=SimpleNamespace(content=content))

    return Client()


def test_classify_splits_fields():
    content = '{"notes": "4 cámaras", "measurements": "20 m", "observations": " techo alto "}'
    with patch("app.ai_engine.nlu.get_client", return_value=_fake_ollama(content)):
        result = classify_voice_transcript("cuatro cámaras veinte metros techo alto")
    assert result == {"notes": "4 cámaras", "measurements": "20 m", "observations": "techo alto", "classified": True}


def test_classify_falls_back_to_notes_when_ollama_fails():
    with patch("app.ai_engine.nlu._call", side_effect=HTTPException(status_code=400, detail="Ollama caído")):
        result = classify_voice_transcript("cuatro cámaras")
    assert result == {"notes": "cuatro cámaras", "measurements": "", "observations": "", "classified": False}


def test_classify_falls_back_when_model_returns_empty_fields():
    content = '{"notes": "", "measurements": "", "observations": ""}'
    with patch("app.ai_engine.nlu.get_client", return_value=_fake_ollama(content)):
        result = classify_voice_transcript("cuatro cámaras")
    assert result["notes"] == "cuatro cámaras"
    assert result["classified"] is False


# --- Aprendizaje: el reparto mejora con las correcciones del técnico -------------------------


def _feedback(client, headers, project_id, ai, final, transcript="cuatro cámaras veinte metros", classified=True):
    return client.post(
        f"/api/projects/{project_id}/survey/voice-feedback",
        json={"transcript": transcript, "ai": ai, "final": final, "classified": classified},
        headers=headers,
    )


def test_voice_feedback_records_correction(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ai = {"notes": "4 cámaras, 20 m", "measurements": "", "observations": ""}
    final = {"notes": "4 cámaras", "measurements": "20 m", "observations": ""}

    resp = _feedback(client, headers, project["id"], ai, final)
    assert resp.status_code == 204, resp.text

    rows = client.get("/api/ai-feedback-events/voice-examples", headers=headers).json()
    assert len(rows) == 1
    assert rows[0]["corrected"] is True
    assert rows[0]["ai_notes"] == "4 cámaras, 20 m"
    assert rows[0]["final_measurements"] == "20 m"


def test_voice_feedback_unchanged_is_not_marked_corrected(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    same = {"notes": "4 cámaras", "measurements": "20 m", "observations": ""}
    # los espacios al borde no cuentan como corrección
    padded = {"notes": " 4 cámaras ", "measurements": "20 m ", "observations": ""}
    assert _feedback(client, headers, project["id"], same, padded).status_code == 204

    assert client.get("/api/ai-feedback-events/voice-examples", headers=headers).json()[0]["corrected"] is False
    assert client.get("/api/ai-feedback-events/voice-examples?corrected_only=true", headers=headers).json() == []


def test_voice_feedback_unknown_project_404_and_requires_auth(client, admin_token):
    body = {"transcript": "x", "ai": {}, "final": {}}
    assert client.post("/api/projects/999999/survey/voice-feedback", json=body, headers=auth_headers(admin_token)).status_code == 404
    assert client.post("/api/projects/1/survey/voice-feedback", json=body).status_code == 401


def test_recent_voice_examples_prefers_corrections_and_skips_long_or_empty(client, admin_token, db_session):
    from app.ai_engine.learning import recent_voice_examples, record_voice_feedback

    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    pid = project["id"]
    accepted = {"notes": "A", "measurements": "", "observations": ""}
    fixed_ai = {"notes": "todo en notas", "measurements": "", "observations": ""}
    fixed = {"notes": "B", "measurements": "5 m", "observations": ""}

    record_voice_feedback(db_session, pid, "dictado aceptado", accepted, accepted, True, None)
    record_voice_feedback(db_session, pid, "dictado corregido", fixed_ai, fixed, True, None)
    record_voice_feedback(db_session, pid, "x" * 701, fixed_ai, fixed, True, None)  # demasiado largo
    record_voice_feedback(db_session, pid, "dictado vacío", accepted, {"notes": "", "measurements": "", "observations": ""}, True, None)
    db_session.commit()

    examples = recent_voice_examples(db_session)
    assert [e["transcript"] for e in examples] == ["dictado corregido", "dictado aceptado"]
    assert examples[0]["measurements"] == "5 m"  # lo que dejó el técnico, no lo de la IA


def test_classify_prompt_includes_learned_examples():
    seen = {}

    class Client:
        def chat(self, **kwargs):
            seen["prompt"] = kwargs["messages"][0]["content"]
            return SimpleNamespace(message=SimpleNamespace(content='{"notes": "n", "measurements": "", "observations": ""}'))

    examples = [{"transcript": "tres puertas quince metros", "notes": "3 puertas", "measurements": "15 m", "observations": ""}]
    with patch("app.ai_engine.nlu.get_client", return_value=Client()):
        classify_voice_transcript("dos cámaras", examples)
    assert "tres puertas quince metros" in seen["prompt"]
    assert '"measurements": "15 m"' in seen["prompt"]
    assert seen["prompt"].rstrip().endswith("Dictado nuevo:\ndos cámaras")

    with patch("app.ai_engine.nlu.get_client", return_value=Client()):
        classify_voice_transcript("dos cámaras")
    assert "Ejemplo 1" not in seen["prompt"]


def test_transcribe_passes_learned_examples_to_classifier(client, admin_token):
    headers = auth_headers(admin_token)
    project = make_project(client, headers)
    ai = {"notes": "todo", "measurements": "", "observations": ""}
    final = {"notes": "4 cámaras", "measurements": "20 m", "observations": ""}
    _feedback(client, headers, project["id"], ai, final, transcript="cuatro cámaras veinte metros")
    asset = _upload_audio(client, headers, project["id"]).json()

    fields = {"notes": "n", "measurements": "", "observations": "", "classified": True}
    with (
        patch("app.api.routers.ai.transcribe_audio", return_value="dos cámaras"),
        patch("app.api.routers.ai.classify_voice_transcript", return_value=fields) as mocked,
    ):
        resp = client.post(f"/api/projects/{project['id']}/survey/assets/{asset['id']}/transcribe", headers=headers)
    assert resp.status_code == 200
    passed = mocked.call_args.args[1]
    assert passed[0]["transcript"] == "cuatro cámaras veinte metros"
    assert passed[0]["measurements"] == "20 m"
