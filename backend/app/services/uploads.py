from fastapi import HTTPException, status

from app.core.config import get_settings


def enforce_upload_size(contents: bytes) -> None:
    """Rechaza archivos subidos que excedan MAX_UPLOAD_MB, antes de escribirlos a disco."""
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"El archivo supera el límite de {settings.max_upload_mb} MB",
        )
