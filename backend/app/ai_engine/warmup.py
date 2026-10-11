"""Precalentamiento de la IA local: carga en memoria el modelo de texto (Ollama) y el de voz
(Whisper) antes de que se necesiten. En CPU el arranque en frío cuesta ~10-12 s por modelo y es lo
que más se nota al empezar un levantamiento.

Todo es best-effort y en segundo plano: nunca bloquea la petición ni propaga errores."""

import logging
import threading
import time

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, get_client
from app.core.config import get_settings

logger = logging.getLogger("multitec.ai")

# No relanzar el precalentamiento mientras hay uno en curso ni más seguido que esto: la app lo pide
# cada vez que se abre un levantamiento y el modelo ya está caliente por `keep_alive`.
MIN_INTERVAL_SECONDS = 120

_lock = threading.Lock()
_last_started = 0.0
_running = False


def _warm() -> None:
    global _running
    started = time.time()
    try:
        settings = get_settings()
        try:
            # Un prompt vacío en `generate` solo carga el modelo, sin generar texto.
            get_client().generate(model=settings.ai_model, prompt="", options=OLLAMA_OPTIONS)
        except Exception:
            logger.info("Precalentamiento: Ollama no respondió; se omite")
        try:
            from app.ai_engine import transcription

            # Mismo candado que la transcripción: así nunca se carga el modelo de voz dos veces.
            with transcription._lock:
                transcription._get_model()
        except Exception:
            logger.info("Precalentamiento: el modelo de voz no se pudo cargar; se omite")
        logger.info("Precalentamiento de IA terminado en %.1f s", time.time() - started)
    finally:
        with _lock:
            _running = False


def start_warmup() -> bool:
    """Lanza el precalentamiento en un hilo. Devuelve True si arrancó uno nuevo, False si ya hay
    uno en curso o se hizo hace muy poco."""
    global _last_started, _running
    with _lock:
        now = time.time()
        if _running or now - _last_started < MIN_INTERVAL_SECONDS:
            return False
        _running = True
        _last_started = now
    threading.Thread(target=_warm, name="ai-warmup", daemon=True).start()
    return True
