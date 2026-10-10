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
# levantamiento (siglas, marcas, unidades, equipos) en vez de homófonos comunes. Con solo siglas
# genéricas el modelo "small" oía "megapíxeles" como "metodopiceles", "Hikvision" como
# "Marqueehibition" y "patch panel" como "Pashpanen"; con marcas y equipos concretos los acierta.
# Ampliar esta lista con las marcas y equipos que de verdad se instalan mejora el dictado sin
# costo de velocidad.
DOMAIN_PROMPT = (
    "Levantamiento técnico de seguridad electrónica en República Dominicana. Vocabulario: "
    "cámaras IP de 2, 4, 5 y 8 megapíxeles, Hikvision, Dahua, Uniview, Ezviz, Hilook, Axis, "
    "Ubiquiti, TP-Link, NVR, DVR, 16 y 32 canales, disco duro, switch PoE de 8, 16 y 24 puertos, "
    "patch panel, rack, gabinete de 6U, 9U y 12U, organizador, bandeja, UPS, regleta, cable UTP "
    "categoría 6, Cat6, conector RJ45, canaleta, tubería EMT, caja de cable, fuente de poder, "
    "balun, access point, router, control de acceso, cerradura magnética, huella, intercom, "
    "videoportero, alarma, sensores, cerco eléctrico."
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
