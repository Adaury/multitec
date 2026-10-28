"""Errores de arranque que reporta el navegador (frontend/public/boot-check.js).

Desde fuera no se ve lo que pasa en un teléfono: una pantalla negra no deja rastro en el servidor. Esto lo deja en el
log. Es PÚBLICO a propósito (la persona todavía no entró; justo falla al abrir), así que se protege: límite por IP,
tamaños topados, sin guardar nada más que lo que llega y sin dejar que el texto rompa el formato del log."""

import logging
import re

from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field

from app.core.limiter import limiter

logger = logging.getLogger("multitec.client")

router = APIRouter(prefix="/api/client-errors", tags=["diagnostics"])

_CONTROL = re.compile(r"[\x00-\x1f\x7f]+")


class ClientError(BaseModel):
    kind: str = Field(default="error", max_length=30)
    message: str = Field(default="", max_length=500)
    detail: str = Field(default="", max_length=1500)
    url: str = Field(default="", max_length=300)


def _one_line(value: str, limit: int) -> str:
    """Sin saltos de línea ni caracteres de control: quien envíe no puede fabricar líneas falsas en el log."""
    return _CONTROL.sub(" ", value)[:limit]


@router.post("", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("20/minute")
def report_client_error(request: Request, payload: ClientError) -> None:
    logger.warning(
        "Error en el navegador [%s] %s | %s | %s | UA=%s | IP=%s",
        _one_line(payload.kind, 30),
        _one_line(payload.message, 500),
        _one_line(payload.detail, 1500),
        _one_line(payload.url, 300),
        _one_line(request.headers.get("user-agent", ""), 200),
        request.client.host if request.client else "?",
    )
