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
