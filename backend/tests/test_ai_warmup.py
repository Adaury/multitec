import time

import pytest

from app.ai_engine import ollama_client, warmup
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def _reset_warmup_state(monkeypatch):
    monkeypatch.setattr(warmup, "_last_started", 0.0)
    monkeypatch.setattr(warmup, "_running", False)


def test_client_keeps_the_model_loaded_by_default(monkeypatch):
    seen = {}

    def fake_chat(self, *args, **kwargs):
        seen.update(kwargs)
        return "ok"

    monkeypatch.setattr(ollama_client.ollama.Client, "chat", fake_chat)
    client = ollama_client.get_client()

    client.chat(model="llama3.2", messages=[])
    assert seen["keep_alive"] == "30m"

    # Quien llama puede pedir otra cosa y se respeta.
    client.chat(model="llama3.2", messages=[], keep_alive="0")
    assert seen["keep_alive"] == "0"


def test_warmup_endpoint_is_accepted_and_throttled(client, admin_token, monkeypatch):
    calls = []
    monkeypatch.setattr(warmup, "_warm", lambda: calls.append(1))
    headers = auth_headers(admin_token)

    first = client.post("/api/ai/warmup", headers=headers)
    assert first.status_code == 202
    assert first.json() == {"started": True}
    time.sleep(0.2)
    assert calls == [1]

    # Dos aperturas seguidas de /nuevo no relanzan la carga.
    again = client.post("/api/ai/warmup", headers=headers)
    assert again.status_code == 202 and again.json() == {"started": False}


def test_warmup_never_fails_when_ollama_and_whisper_are_down(monkeypatch):
    class Boom:
        def generate(self, *a, **k):
            raise RuntimeError("ollama caído")

    monkeypatch.setattr(warmup, "get_client", lambda: Boom())
    from app.ai_engine import transcription

    monkeypatch.setattr(transcription, "_get_model", lambda: (_ for _ in ()).throw(RuntimeError("sin modelo")))

    warmup._running = True
    warmup._warm()  # no debe lanzar

    assert warmup._running is False


def test_warmup_requires_login(client):
    assert client.post("/api/ai/warmup").status_code in (401, 403)
