import logging
from pathlib import Path

import ollama
from fastapi import HTTPException

from app.core.config import get_settings

SUPPORTED_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
MAX_IMAGES = 6

logger = logging.getLogger("multitec.ai")

# El GPU local de esta máquina produce texto corrupto en la inferencia (confirmado: mismo
# prompt, mismo modelo, solo CPU da una respuesta coherente) — se fuerza CPU en todas las
# llamadas hasta que se resuelva el driver/GPU. Más lento, pero confiable.
OLLAMA_OPTIONS = {"num_gpu": 0}


def get_client() -> ollama.Client:
    settings = get_settings()
    return ollama.Client(host=settings.ollama_host)


def _call(fn):
    try:
        return fn()
    except HTTPException:
        raise
    except Exception as e:
        # El detalle completo de la excepción se registra en el log del servidor, no se
        # le manda al cliente — puede incluir rutas internas o detalles de conexión.
        logger.exception("Fallo llamando a Ollama")
        raise HTTPException(
            status_code=400,
            detail=(
                "Ollama no está corriendo o falta un modelo. Instala Ollama desde "
                "https://ollama.com, luego ejecuta 'ollama pull llama3.2' y "
                f"'ollama pull llava'. ({type(e).__name__})"
            ),
        )


def load_image_paths(file_paths: list[str], limit: int = MAX_IMAGES) -> list[str]:
    """Filtra fotos del disco a formatos soportados por el modelo de visión local.

    Omite formatos no soportados (p. ej. HEIC de iPhone) en vez de fallar — el análisis
    continúa solo con las imágenes compatibles.
    """
    paths: list[str] = []
    for path_str in file_paths:
        if len(paths) >= limit:
            break
        path = Path(path_str)
        if path.suffix.lower() in SUPPORTED_IMAGE_TYPES and path.exists():
            paths.append(str(path))
    return paths


REFUSAL_MARKERS = (
    "lo siento",
    "disculpe",
    "no puedo ayudarte",
    "no puedo proporcionar",
    "no puedo procesar",
    "no puedo describir",
    "no contiene imagen",
    "no contiene imágenes",
    "no hay imagen",
    "no hay imágenes",
    "no hay ninguna imagen",
    "sin imagen adjunta",
    "sin imágenes adjuntas",
    "no imágenes adjuntas",
    "no veo ninguna imagen",
    "no veo imagen",
    "no se proporcionó ninguna imagen",
    "no proporcionaste imagen",
    "asegúrate de agregarlas",
)

# Frases que casi nunca aparecen al inicio de una descripción real de imagen, sin importar
# qué tan larga sea la negativa (p. ej. negativas "por sensibilidad" con explicaciones largas).
OPENING_REFUSAL_MARKERS = ("lo siento", "disculpe", "no puedo")


def looks_like_refusal(text: str) -> bool:
    """El modelo de visión local (llava, 7B cuantizado en CPU) a veces produce falsos
    positivos de negativa ante fotos de cámaras/seguridad, o pierde la imagen de vista con
    prompts largos. Se detecta heurísticamente para reintentar en vez de mostrar basura."""
    lowered = text.strip().lower()
    if any(marker in lowered[:40] for marker in OPENING_REFUSAL_MARKERS):
        return True
    return len(lowered) < 220 and any(marker in lowered for marker in REFUSAL_MARKERS)
