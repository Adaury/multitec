"""Transcripción de voz 100% local (faster-whisper) para el levantamiento por voz.

El modelo se carga una sola vez por proceso (perezosamente: no se descarga ni se ocupa
memoria hasta la primera nota de voz) y se serializa con un lock — Whisper en CPU ya usa
todos los núcleos, así que dos transcripciones en paralelo solo se estorbarían.
"""

import logging
import threading
from pathlib import Path

from fastapi import HTTPException

from app.core.config import get_settings

logger = logging.getLogger("multitec.ai")

# Vocabulario del oficio: sesga a Whisper hacia los términos que un técnico dice en un
# levantamiento (siglas, marcas de cable, unidades) en vez de homófonos comunes.
DOMAIN_PROMPT = (
    "Levantamiento técnico de seguridad electrónica en República Dominicana: cámaras CCTV, "
    "DVR, NVR, cable UTP Cat6, metros de cable, canaletas, tubería, switch PoE, router, "
    "access point, control de acceso, cerradura magnética, intercom, alarma, sensores."
)

_model = None
_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        from faster_whisper import WhisperModel

        settings = get_settings()
        _model = WhisperModel(settings.whisper_model, device="cpu", compute_type=settings.whisper_compute_type)
    return _model


def transcribe_audio(path: str | Path) -> str:
    """Devuelve el texto en español del audio. Lanza HTTPException 400 si falla (modelo sin
    descargar, audio ilegible…); el detalle técnico queda solo en el log del servidor."""
    try:
        with _lock:
            segments, _info = _get_model().transcribe(
                str(path),
                language="es",
                vad_filter=True,  # descarta silencios/ruido de obra, evita alucinaciones
                initial_prompt=DOMAIN_PROMPT,
            )
            text = " ".join(segment.text.strip() for segment in segments)
    except Exception as e:
        logger.exception("Fallo transcribiendo audio %s", path)
        raise HTTPException(
            status_code=400,
            detail=f"No se pudo transcribir el audio. Intenta grabar de nuevo. ({type(e).__name__})",
        )
    return text.strip()
