"""Cliente de Gemini: mismo formato que Ollama, sin tocar Google (se simula con httpx.MockTransport)."""

import io
import json
import math
import struct
import wave
from types import SimpleNamespace

import httpx
import pytest
from fastapi import HTTPException

from app.ai_engine import gemini_client, ollama_client, transcription, warmup
from app.ai_engine.gemini_client import GeminiClient, GeminiError
from app.api.routers import system
from app.core.config import get_settings

KEY = "CLAVE-SECRETA-DE-PRUEBA"


def _settings(**over):
    base = dict(
        gemini_api_key=KEY,
        gemini_model="gemini-test",
        gemini_embedding_model="emb-test",
        gemini_embedding_dims=768,
        gemini_thinking_budget=0,
        ai_provider="gemini",
    )
    base.update(over)
    return SimpleNamespace(**base)


def _ok(text):
    return {"candidates": [{"content": {"parts": [{"text": text}]}}]}


def _client(handler, **over):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return GeminiClient(_settings(**over), client=http)


@pytest.fixture(autouse=True)
def _no_sleep(monkeypatch):
    monkeypatch.setattr(gemini_client.time, "sleep", lambda s: None)


def _png_bytes(size=(3000, 2000)):
    from PIL import Image

    out = io.BytesIO()
    Image.new("RGB", size, (200, 30, 30)).save(out, format="PNG")
    return out.getvalue()


def test_chat_text_returns_content_and_key_only_in_header():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["key_header"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ok("Hola técnico"))

    r = _client(handler).chat(model="llama3.2", messages=[{"role": "user", "content": "hola"}], options={"num_gpu": 0})
    assert r.message.content == "Hola técnico"
    assert seen["key_header"] == KEY
    assert KEY not in seen["url"]  # nunca en la URL
    assert "models/gemini-test:generateContent" in seen["url"]  # ignora el nombre de modelo de Ollama
    assert seen["body"]["contents"] == [{"role": "user", "parts": [{"text": "hola"}]}]
    assert seen["body"]["generationConfig"]["thinkingConfig"] == {"thinkingBudget": 0}


def test_roles_system_and_assistant_are_mapped():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ok("ok"))

    _client(handler).chat(
        messages=[
            {"role": "system", "content": "Eres un asistente."},
            {"role": "user", "content": "uno"},
            {"role": "assistant", "content": "dos"},
            {"role": "user", "content": "tres"},
        ]
    )
    body = seen["body"]
    assert body["systemInstruction"]["parts"][0]["text"] == "Eres un asistente."
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]


def test_small_num_predict_gets_a_floor_and_temperature_passes():
    seen = {}

    def handler(request):
        seen["cfg"] = json.loads(request.content)["generationConfig"]
        return httpx.Response(200, json=_ok("x"))

    _client(handler).chat(messages=[{"role": "user", "content": "a"}], options={"num_predict": 40, "temperature": 0})
    assert seen["cfg"]["maxOutputTokens"] == gemini_client.MIN_OUTPUT_TOKENS
    assert seen["cfg"]["temperature"] == 0


def test_json_schema_sets_json_mode_and_is_in_prompt():
    schema = {"type": "object", "properties": {"intent": {"type": "string"}}, "required": ["intent"]}
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_ok('{"intent": "agenda"}'))

    r = _client(handler).chat(messages=[{"role": "user", "content": "qué tengo hoy"}], format=schema)
    assert json.loads(r.message.content) == {"intent": "agenda"}
    cfg = seen["body"]["generationConfig"]
    assert cfg["responseMimeType"] == "application/json"
    assert cfg["responseJsonSchema"] == schema
    assert "esquema" in seen["body"]["systemInstruction"]["parts"][0]["text"]


def test_schema_falls_back_when_native_schema_is_rejected():
    calls = []

    def handler(request):
        cfg = json.loads(request.content)["generationConfig"]
        calls.append("responseJsonSchema" in cfg)
        if "responseJsonSchema" in cfg:
            return httpx.Response(400, json={"error": {"message": "schema no soportado"}})
        return httpx.Response(200, json=_ok('{"a": 1}'))

    r = _client(handler).chat(messages=[{"role": "user", "content": "x"}], format={"type": "object"})
    assert json.loads(r.message.content) == {"a": 1}
    assert calls == [True, False]


def test_images_are_downscaled_and_sent_inline_from_path_and_bytes(tmp_path):
    photo = tmp_path / "foto.png"
    photo.write_bytes(_png_bytes())
    seen = {}

    def handler(request):
        seen["parts"] = json.loads(request.content)["contents"][0]["parts"]
        return httpx.Response(200, json=_ok("veo una cámara"))

    r = _client(handler).chat(
        messages=[{"role": "user", "content": "describe", "images": [str(photo), _png_bytes((800, 600))]}]
    )
    assert r.message.content == "veo una cámara"
    inline = [p["inline_data"] for p in seen["parts"] if "inline_data" in p]
    assert len(inline) == 2
    assert all(i["mime_type"] == "image/jpeg" for i in inline)
    import base64
    from PIL import Image

    big = Image.open(io.BytesIO(base64.b64decode(inline[0]["data"])))
    assert max(big.size) <= gemini_client.MAX_IMAGE_SIDE


def test_retries_on_429_then_succeeds():
    attempts = []

    def handler(request):
        attempts.append(1)
        if len(attempts) < 3:
            return httpx.Response(429, json={"error": {"message": "cuota"}})
        return httpx.Response(200, json=_ok("listo"))

    assert _client(handler).chat(messages=[{"role": "user", "content": "a"}]).message.content == "listo"
    assert len(attempts) == 3


def test_persistent_429_gives_friendly_error_without_key():
    def handler(request):
        return httpx.Response(429, text=f"quota exceeded for key {KEY}")

    with pytest.raises(GeminiError) as exc:
        _client(handler).chat(messages=[{"role": "user", "content": "a"}])
    assert "límite" in exc.value.user_message
    assert KEY not in exc.value.user_message


def test_network_error_does_not_leak_url_or_key():
    def handler(request):
        raise httpx.ConnectError(f"no route to {request.url}")

    with pytest.raises(GeminiError) as exc:
        _client(handler).chat(messages=[{"role": "user", "content": "a"}])
    assert KEY not in exc.value.user_message and "googleapis" not in exc.value.user_message


def test_missing_key_is_a_clear_error():
    with pytest.raises(GeminiError) as exc:
        _client(lambda r: httpx.Response(200, json=_ok("x")), gemini_api_key="").chat(
            messages=[{"role": "user", "content": "a"}]
        )
    assert "GEMINI_API_KEY" in exc.value.user_message


def test_blocked_prompt_is_reported():
    def handler(request):
        return httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}})

    with pytest.raises(GeminiError) as exc:
        _client(handler).chat(messages=[{"role": "user", "content": "a"}])
    assert "SAFETY" in exc.value.user_message


def test_embed_returns_vector_in_ollama_shape():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"embedding": {"values": [0.1, 0.2, 0.3]}})

    r = _client(handler).embed(model="nomic-embed-text", input="expediente")
    assert list(r.embeddings[0]) == [0.1, 0.2, 0.3]
    assert "models/emb-test:embedContent" in seen["url"]
    assert seen["body"]["outputDimensionality"] == 768
    assert seen["body"]["content"]["parts"][0]["text"] == "expediente"


def test_generate_works_for_warmup_style_calls():
    r = _client(lambda req: httpx.Response(200, json=_ok("hola"))).generate(model="x", prompt="")
    assert r.response == "hola"


# ── Voz ─────────────────────────────────────────────────────────────────────
def _make_audio(tmp_path, name="nota.wav", seconds=0.5, rate=44100):
    path = tmp_path / name
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(
            struct.pack("<hh", v, v)
            for v in (int(12000 * math.sin(2 * math.pi * 440 * i / rate)) for i in range(int(rate * seconds)))
        )
        w.writeframes(frames)
    return path


def test_audio_is_converted_to_16k_mono_wav(tmp_path):
    wav = gemini_client.audio_to_wav_bytes(_make_audio(tmp_path))
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getnchannels(), w.getframerate(), w.getsampwidth()) == (1, 16000, 2)
        assert w.getnframes() > 16000 * 0.4


def test_transcribe_sends_wav_and_vocabulary(tmp_path):
    seen = {}

    def handler(request):
        seen["parts"] = json.loads(request.content)["contents"][0]["parts"]
        return httpx.Response(200, json=_ok("  instalar cuatro cámaras Hikvision  "))

    text = _client(handler).transcribe(_make_audio(tmp_path), vocabulary="Hikvision, Dahua")
    assert text == "instalar cuatro cámaras Hikvision"
    assert "Hikvision, Dahua" in seen["parts"][0]["text"]
    assert seen["parts"][1]["inline_data"]["mime_type"] == "audio/wav"


def test_transcribe_audio_uses_gemini_when_provider_is_gemini(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "ai_provider", "gemini")
    monkeypatch.setattr(GeminiClient, "transcribe", lambda self, path, vocabulary="": f"oído:{vocabulary[:5]}")
    monkeypatch.setattr(transcription, "_get_model", lambda: pytest.fail("no debe cargar Whisper con Gemini"))
    assert transcription.transcribe_audio(tmp_path / "x.m4a", initial_prompt="abcdefgh") == "oído:abcde"


def test_transcribe_audio_maps_gemini_error_to_400(monkeypatch, tmp_path):
    monkeypatch.setattr(get_settings(), "ai_provider", "gemini")

    def boom(self, path, vocabulary=""):
        raise GeminiError("Gemini alcanzó su límite.")

    monkeypatch.setattr(GeminiClient, "transcribe", boom)
    with pytest.raises(HTTPException) as exc:
        transcription.transcribe_audio(tmp_path / "x.m4a")
    assert exc.value.status_code == 400 and "límite" in exc.value.detail


# ── Selector de proveedor ───────────────────────────────────────────────────
def test_get_client_defaults_to_ollama_and_switches_to_gemini(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_provider", "ollama")
    assert isinstance(ollama_client.get_client(), ollama_client.ollama.Client)
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    assert isinstance(ollama_client.get_client(), GeminiClient)


def test_call_maps_gemini_error_to_http_400():
    def fn():
        raise GeminiError("Gemini rechazó la clave. Revisa GEMINI_API_KEY.")

    with pytest.raises(HTTPException) as exc:
        ollama_client._call(fn)
    assert exc.value.status_code == 400 and "GEMINI_API_KEY" in exc.value.detail


def test_warmup_does_nothing_with_gemini(monkeypatch):
    monkeypatch.setattr(get_settings(), "ai_provider", "gemini")
    monkeypatch.setattr(warmup, "get_client", lambda: pytest.fail("no debe llamar a la IA"))
    warmup._running = True
    warmup._warm()
    assert warmup._running is False


def test_status_reports_ready_only_with_key(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "ai_provider", "gemini")
    monkeypatch.setattr(settings, "gemini_api_key", "")
    assert system._check_ai()["reachable"] is False
    monkeypatch.setattr(settings, "gemini_api_key", KEY)
    status = system._check_ai()
    assert status["reachable"] and status["installed"] and status["model"] == settings.gemini_model
