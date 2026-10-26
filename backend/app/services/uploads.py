from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.tenant import TenantContextError


def company_dir(db: Session, *parts: str) -> Path:
    """Carpeta de archivos de la empresa de la sesión: `uploads/c{id}/...`. Cada empresa guarda en la suya, y
    `/uploads` solo sirve a cada una lo que está en la suya (los archivos anteriores a multi-empresa, sin prefijo,
    son de la empresa 1)."""
    company_id = db.info.get("company_id")
    if company_id is None:
        raise TenantContextError("No se puede guardar un archivo sin empresa activa")
    return Path(get_settings().upload_dir, f"c{company_id}", *parts)


def can_read_upload(company_id: int, relative_path: str) -> bool:
    """¿Esta empresa puede leer ese archivo? Prefijo `c{id}/` = solo esa empresa; sin prefijo (archivos de antes de
    multi-empresa) = solo la empresa 1."""
    first = relative_path.replace("\\", "/").lstrip("/").split("/", 1)[0]
    if first.startswith("c") and first[1:].isdigit():
        return int(first[1:]) == company_id
    return company_id == 1

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


_CHUNK = 1024 * 1024


async def read_upload(file) -> bytes:
    """Lee un archivo subido por bloques y corta al pasar MAX_UPLOAD_MB. Con `await file.read()` entero,
    varias subidas enormes en paralelo agotaban la memoria antes de que se revisara el tamaño."""
    settings = get_settings()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK):
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"El archivo supera el límite de {settings.max_upload_mb} MB",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def _is_image(head: bytes, base_type: str) -> bool:
    if base_type == "image/jpeg":
        return head.startswith(b"\xff\xd8\xff")
    if base_type == "image/png":
        return head.startswith(b"\x89PNG\r\n\x1a\n")
    if base_type == "image/webp":
        return head[:4] == b"RIFF" and head[8:12] == b"WEBP"
    if base_type == "image/heic":
        # Contenedor ISO (ftyp) con una marca HEIF/HEIC.
        return head[4:8] == b"ftyp" and head[8:12] in (b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1", b"heim", b"heis")
    return False


# Lo que un audio nunca es: si empieza así, no es una nota de voz sino otra cosa disfrazada.
_NOT_AUDIO_STARTS = (b"<", b"%PDF", b"MZ", b"PK\x03\x04", b"\x7fELF", b"#!", b"GIF8")


def enforce_matches_declared_type(contents: bytes, content_type: str | None) -> None:
    """Comprueba que el contenido corresponde al tipo que declara el cliente (los primeros bytes, no el nombre
    ni la cabecera, que el cliente controla). Un archivo cualquiera declarado "image/png" no se guarda: acaba
    en Pillow, en los PDF y en el navegador de otros usuarios. En imágenes es estricto; en audio solo
    rechaza lo que claramente es otra cosa (la transcripción ya falla limpiamente con audio dañado)."""
    base_type = (content_type or "").split(";")[0].strip().lower()
    head = contents[:16]
    if base_type.startswith("image/"):
        if not _is_image(head, base_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo no es una imagen válida del tipo indicado",
            )
    elif base_type.startswith("audio/") or base_type in ("video/mp4", "video/webm", "application/octet-stream"):
        if head.startswith(_NOT_AUDIO_STARTS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El archivo no es un audio válido",
            )
