import logging
import time

import ollama
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.ai_engine import transcription
from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db

logger = logging.getLogger("multitec.system")

router = APIRouter(prefix="/api/system", tags=["system"])

allowed_roles = require_role("admin", "oficina", "tecnico")

# Ollama local responde en milisegundos; si tarda más de esto, para el usuario es como si no
# estuviera. El chequeo nunca debe colgar la pantalla de estado.
OLLAMA_CHECK_TIMEOUT_SECONDS = 2.0


def _check_database(db: Session) -> bool:
    try:
        db.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        logger.exception("Chequeo de estado: la base de datos no responde")
        return False


def _check_ai() -> dict:
    """Estado de la IA de texto: si Ollama responde, si el modelo está descargado y si ya está
    cargado en memoria (caliente = la primera respuesta es rápida)."""
    settings = get_settings()
    model = settings.ai_model
    try:
        client = ollama.Client(host=settings.ollama_host, timeout=OLLAMA_CHECK_TIMEOUT_SECONDS)
        installed = {m.model.split(":")[0] for m in client.list().models if m.model}
        running = {m.model.split(":")[0] for m in client.ps().models if m.model}
    except Exception:  # noqa: BLE001
        return {"reachable": False, "model": model, "installed": False, "warm": False}
    base = model.split(":")[0]
    return {"reachable": True, "model": model, "installed": base in installed, "warm": base in running}


@router.get("/status")
def get_status(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Una mirada a la salud del sistema para el indicador de la app. `overall`:
    `ok` (todo listo), `degraded` (se puede trabajar, pero sin IA o con IA fría) o `down`
    (sin base de datos). Solo lectura y rápido: no carga ningún modelo."""
    started = time.time()
    database = _check_database(db)
    ai = _check_ai()

    if not database:
        overall = "down"
    elif not (ai["reachable"] and ai["installed"]):
        overall = "degraded"
    else:
        overall = "ok"

    return {
        "overall": overall,
        "api": True,
        "database": database,
        "ai": ai,
        "voice_loaded": transcription._model is not None,
        "checked_in_ms": round((time.time() - started) * 1000),
    }
