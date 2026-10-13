from types import SimpleNamespace

from app.api.routers import system
from tests.conftest import auth_headers


def _fake_ollama(monkeypatch, installed=("llama3.2:latest",), running=(), fail=False):
    class FakeClient:
        def __init__(self, *args, **kwargs):
            if fail:
                raise ConnectionError("ollama apagado")

        def list(self):
            return SimpleNamespace(models=[SimpleNamespace(model=m) for m in installed])

        def ps(self):
            return SimpleNamespace(models=[SimpleNamespace(model=m) for m in running])

    monkeypatch.setattr(system.ollama, "Client", FakeClient)


def test_status_requires_authentication(client):
    assert client.get("/api/system/status").status_code in (401, 403)


def test_everything_ready_reports_ok_and_warm_model(client, admin_token, monkeypatch):
    _fake_ollama(monkeypatch, running=("llama3.2:latest",))

    body = client.get("/api/system/status", headers=auth_headers(admin_token)).json()

    assert body["overall"] == "ok"
    assert body["database"] is True
    assert body["ai"] == {"reachable": True, "model": "llama3.2", "installed": True, "warm": True}


def test_cold_model_is_still_ok(client, admin_token, monkeypatch):
    _fake_ollama(monkeypatch, running=())

    body = client.get("/api/system/status", headers=auth_headers(admin_token)).json()

    assert body["overall"] == "ok"
    assert body["ai"]["warm"] is False


def test_ollama_down_is_degraded_not_an_error(client, admin_token, monkeypatch):
    _fake_ollama(monkeypatch, fail=True)

    resp = client.get("/api/system/status", headers=auth_headers(admin_token))

    assert resp.status_code == 200
    assert resp.json()["overall"] == "degraded"
    assert resp.json()["ai"]["reachable"] is False


def test_missing_model_is_degraded(client, admin_token, monkeypatch):
    _fake_ollama(monkeypatch, installed=("otro-modelo:latest",))

    body = client.get("/api/system/status", headers=auth_headers(admin_token)).json()

    assert body["overall"] == "degraded"
    assert body["ai"]["installed"] is False


def test_technician_can_see_status(client, tecnico_token, monkeypatch):
    _fake_ollama(monkeypatch)

    assert client.get("/api/system/status", headers=auth_headers(tecnico_token)).status_code == 200
