from fastapi import HTTPException, status

from app.core.config import get_settings

# La extensión con la que se guarda un archivo sale del tipo ya validado, nunca del nombre que
# manda el cliente: de lo contrario "x.html" declarado como image/png se serviría desde /uploads
# como página web, en el mismo origen que guarda la sesión de la app (XSS almacenado).
_EXTENSION_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/heic": ".heic",
    "image/webp": ".webp",
    "audio/mpeg": ".mp3",
    "audio/mp4": ".m4a",
    "audio/m4a": ".m4a",
    "audio/x-m4a": ".m4a",
    "audio/wav": ".wav",
    "audio/webm": ".webm",
}


def stored_extension(content_type: str | None) -> str:
    """Extensión segura para un tipo de contenido ya validado (sin parámetros como ';codecs=')."""
    base_type = (content_type or "").split(";")[0].strip().lower()
    return _EXTENSION_BY_TYPE.get(base_type, ".bin")


def enforce_upload_size(contents: bytes) -> None:
    """Rechaza archivos subidos que excedan MAX_UPLOAD_MB, antes de escribirlos a disco."""
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.max_upload_mb} MB",
        )
