"""Cliente de Gemini (Google) con la MISMA forma que el cliente de Ollama.

Todo el motor de IA llama `get_client().chat(model=..., messages=[...], format=<esquema>, options=...)` y lee
`response.message.content`; los embeddings usan `client.embed(...)` → `response.embeddings[0]`. Este cliente imita
esa forma, así que activar Gemini (AI_PROVIDER=gemini) no obliga a tocar ningún punto de uso.

Diferencias a tener presentes:
- El nombre de modelo que pasa quien llama ("llama3.2", "llava", "nomic-embed-text") se IGNORA: en modo Gemini
  mandan GEMINI_MODEL y GEMINI_EMBEDDING_MODEL (el mismo modelo ve texto y fotos).
- La clave va en la cabecera `x-goog-api-key`, nunca en la URL: los mensajes de error de HTTP incluyen la URL y
  la clave acabaría en el log (mismo cuidado que en ZuraEdu).
- Nada de lo que viaja aquí se queda en el servidor: es una llamada HTTP hacia Google. Los datos de clientes que
  vayan en el prompt salen de este servidor; ver las condiciones del plan de Gemini que se use.
"""

import base64
import io
import json
import logging
import time
import wave
from pathlib import Path
from types import SimpleNamespace

import httpx

logger = logging.getLogger("multitec.ai")

API_BASE = "https://generativelanguage.googleapis.com/v1beta"
RETRY_STATUSES = {429, 500, 502, 503, 504}
MAX_ATTEMPTS = 3
DEFAULT_MAX_OUTPUT_TOKENS = 2048
# Ollama recibía topes muy chicos (p. ej. 40 tokens para una intención). Con Gemini un tope tan justo corta el
# JSON a medias; el costo de dar margen es mínimo porque la respuesta real sigue siendo corta.
MIN_OUTPUT_TOKENS = 256
# Lado mayor de las fotos que se envían. Un teléfono entrega 4000+ px; con 6 fotos se pasaría del límite de ~20 MB
# por petición y se pagarían tokens de más sin ganar nitidez útil.
MAX_IMAGE_SIDE = 1600


class GeminiError(Exception):
    """Fallo al hablar con Gemini. `user_message` es seguro de mostrar (sin clave, URL ni rutas)."""

    def __init__(self, user_message: str, status: int | None = None):
        super().__init__(user_message)
        self.user_message = user_message
        self.status = status


def _sniff_image_mime(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:4] == b"GIF8":
        return "image/gif"
    if data[4:12] in (b"ftypheic", b"ftypheix", b"ftypmif1"):
        return "image/heic"
    if data[:4] == b"%PDF":
        return "application/pdf"
    return "image/jpeg"


def _prepare_image(data: bytes) -> tuple[str, bytes]:
    """Reduce la foto (lado mayor MAX_IMAGE_SIDE, JPEG). Si no se puede leer con Pillow se envía tal cual."""
    mime = _sniff_image_mime(data)
    if mime == "application/pdf":
        return mime, data
    try:
        from PIL import Image, ImageOps

        with Image.open(io.BytesIO(data)) as img:
            img = ImageOps.exif_transpose(img)  # respeta la orientación con que se tomó la foto
            img.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE))
            out = io.BytesIO()
            img.convert("RGB").save(out, format="JPEG", quality=85)
            return "image/jpeg", out.getvalue()
    except Exception:  # noqa: BLE001 — formato raro: mejor mandarlo crudo que perder la foto
        return mime, data


def _inline_part(mime: str, data: bytes) -> dict:
    return {"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode("ascii")}}


def _image_part(image) -> dict:
    data = image if isinstance(image, (bytes, bytearray)) else Path(str(image)).read_bytes()
    mime, data = _prepare_image(bytes(data))
    return _inline_part(mime, data)


def audio_to_wav_bytes(path: str | Path) -> bytes:
    """Decodifica cualquier audio (m4a/mp4 de iPhone, webm, ogg, wav…) a WAV mono de 16 kHz. Así Gemini recibe un
    formato que seguro acepta, sin depender de qué contenedor grabó el teléfono. Usa PyAV (ya instalado)."""
    import av

    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    pcm = bytearray()
    with av.open(str(path)) as container:
        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise GeminiError("El archivo no tiene audio.")
        for frame in container.decode(stream):
            for out in resampler.resample(frame):
                pcm += out.to_ndarray().tobytes()
        for out in resampler.resample(None):
            pcm += out.to_ndarray().tobytes()
    if not pcm:
        raise GeminiError("El audio está vacío.")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16000)
        wav.writeframes(bytes(pcm))
    return buf.getvalue()


class GeminiClient:
    def __init__(self, settings, client: httpx.Client | None = None):
        self._settings = settings
        self._http = client or httpx.Client(timeout=60.0)

    # ── HTTP ────────────────────────────────────────────────────────────────
    def _post(self, path: str, payload: dict) -> dict:
        key = self._settings.gemini_api_key
        if not key:
            raise GeminiError("Falta configurar la clave de Gemini (GEMINI_API_KEY en el .env del servidor).")
        last: GeminiError | None = None
        for attempt in range(1, MAX_ATTEMPTS + 1):
            try:
                response = self._http.post(
                    f"{API_BASE}/{path}",
                    headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                    json=payload,
                )
            except httpx.HTTPError as e:
                # El texto de la excepción puede traer la URL: se registra solo el tipo.
                logger.warning("Gemini: fallo de red (%s), intento %d", type(e).__name__, attempt)
                last = GeminiError("No se pudo conectar con el servicio de IA (Gemini). Intenta de nuevo en un momento.")
            else:
                if response.status_code < 400:
                    return response.json()
                logger.warning("Gemini: HTTP %s: %s", response.status_code, response.text[:500])
                if response.status_code == 429:
                    msg = "El servicio de IA (Gemini) alcanzó su límite de uso. Espera un minuto e intenta de nuevo."
                elif response.status_code in (401, 403):
                    msg = "Gemini rechazó la clave. Revisa GEMINI_API_KEY."
                elif response.status_code >= 500:
                    msg = "El servicio de IA (Gemini) no está disponible ahora. Intenta de nuevo en un momento."
                else:
                    msg = "Gemini no pudo procesar la solicitud."
                last = GeminiError(msg, status=response.status_code)
                if response.status_code not in RETRY_STATUSES:
                    raise last
            if attempt < MAX_ATTEMPTS:
                time.sleep(1.5 * attempt)
        assert last is not None
        raise last

    @staticmethod
    def _text_of(data: dict) -> str:
        candidates = data.get("candidates") or []
        if not candidates:
            block = (data.get("promptFeedback") or {}).get("blockReason")
            raise GeminiError("Gemini no dio respuesta" + (f" (bloqueada: {block})." if block else "."))
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if isinstance(p, dict))

    # ── Interfaz estilo Ollama ──────────────────────────────────────────────
    def _generate(self, model_path: str, system: str, contents: list[dict], options: dict, schema: dict | None) -> str:
        config: dict = {"maxOutputTokens": max(int(options.get("num_predict") or DEFAULT_MAX_OUTPUT_TOKENS), MIN_OUTPUT_TOKENS)}
        if options.get("temperature") is not None:
            config["temperature"] = options["temperature"]
        budget = self._settings.gemini_thinking_budget
        if budget is not None and budget >= 0:
            # Sin esto, gemini-2.5 gasta parte del tope de salida "pensando" y puede devolver el JSON vacío.
            config["thinkingConfig"] = {"thinkingBudget": budget}
        if schema is not None:
            config["responseMimeType"] = "application/json"
            system = (system + "\n\n" if system else "") + (
                "Responde ÚNICAMENTE con un objeto JSON válido que cumpla este esquema, sin texto adicional:\n"
                + json.dumps(schema, ensure_ascii=False)
            )
        payload: dict = {"contents": contents, "generationConfig": config}
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}

        if schema is not None:
            # Esquema nativo si la API lo acepta; si responde 400 se reintenta sin él (el esquema ya va en el texto).
            native = {**payload, "generationConfig": {**config, "responseJsonSchema": schema}}
            try:
                return self._text_of(self._post(f"{model_path}:generateContent", native))
            except GeminiError as e:
                if e.status != 400:
                    raise
                logger.info("Gemini rechazó responseJsonSchema; se reintenta con el esquema solo en el prompt")
        return self._text_of(self._post(f"{model_path}:generateContent", payload))

    def chat(self, model=None, messages=None, format=None, options=None, **_ignored):  # noqa: A002 — mismo nombre que Ollama
        system_parts: list[str] = []
        contents: list[dict] = []
        for message in messages or []:
            role = message.get("role", "user")
            text = message.get("content") or ""
            if role == "system":
                system_parts.append(text)
                continue
            parts: list[dict] = [{"text": text}] if text else []
            for image in message.get("images") or []:
                parts.append(_image_part(image))
            if parts:
                contents.append({"role": "model" if role == "assistant" else "user", "parts": parts})
        schema = format if isinstance(format, dict) else None
        text = self._generate(
            f"models/{self._settings.gemini_model}", "\n\n".join(system_parts), contents, options or {}, schema
        )
        return SimpleNamespace(message=SimpleNamespace(content=text))

    def generate(self, model=None, prompt="", options=None, **_ignored):
        contents = [{"role": "user", "parts": [{"text": prompt or "Hola"}]}]
        text = self._generate(f"models/{self._settings.gemini_model}", "", contents, options or {}, None)
        return SimpleNamespace(response=text)

    def embed(self, model=None, input="", **_ignored):  # noqa: A002
        name = self._settings.gemini_embedding_model
        payload: dict = {"model": f"models/{name}", "content": {"parts": [{"text": input}]}}
        dims = self._settings.gemini_embedding_dims
        if dims:
            payload["outputDimensionality"] = dims
        data = self._post(f"models/{name}:embedContent", payload)
        values = (data.get("embedding") or {}).get("values")
        if not values:
            raise GeminiError("Gemini no devolvió el vector de búsqueda.")
        return SimpleNamespace(embeddings=[list(values)])

    def transcribe(self, path: str | Path, vocabulary: str = "") -> str:
        """Audio → texto en español con el mismo modelo. `vocabulary` es la frase de términos del oficio que
        ya usaba Whisper como `initial_prompt`: aquí ayuda a escribir bien marcas y nombres."""
        wav = audio_to_wav_bytes(path)
        instruction = (
            "Transcribe este audio en español, palabra por palabra y sin resumir. Responde SOLO con la transcripción. "
            "Si no se entiende nada, responde con una cadena vacía."
        )
        if vocabulary:
            instruction += f"\nContexto y vocabulario que puede aparecer (escribe bien estos términos): {vocabulary}"
        contents = [{"role": "user", "parts": [{"text": instruction}, _inline_part("audio/wav", wav)]}]
        return self._generate(f"models/{self._settings.gemini_model}", "", contents, {"temperature": 0, "num_predict": 4096}, None).strip()
