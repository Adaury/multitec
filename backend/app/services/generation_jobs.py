"""Generación de cotizaciones con IA como trabajo del SERVIDOR, no de la pantalla.

Antes la app mandaba una sola petición larga (1 a 3 minutos) y esperaba la respuesta. Si el técnico cambiaba de
aplicación en el iPhone, Safari suspendía la página, la petición se cortaba y al volver la app mostraba un error
aunque el servidor siguiera trabajando (y al reintentar se creaba una segunda cotización). Ahora:

  - `start` arranca la generación en un hilo y responde enseguida;
  - la app consulta `status` cada pocos segundos, y al volver a abrirla pregunta cuáles trabajos hay;
  - el resultado queda guardado aquí hasta que se lo lleve (una hora).

Vive en memoria del proceso (una sola instancia del servidor): si el servidor se reinicia a mitad de una generación
el trabajo se pierde y la app lo explica, sin crear nada duplicado (la cotización solo se guarda al terminar).
"""

import logging
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from fastapi import HTTPException
from sqlalchemy.orm import Session

logger = logging.getLogger("multitec.ai")

STUCK_AFTER_SECONDS = 20 * 60  # si pasa de aquí sin terminar, se da por perdido y se permite reintentar
KEEP_FINISHED_SECONDS = 60 * 60


@dataclass
class Job:
    project_id: int
    user_id: int
    company_id: int
    label: str
    started_at: float
    status: str = "running"  # running | done | error
    finished_at: float | None = None
    result: dict | None = None
    error: str | None = None


_jobs: dict[int, Job] = {}
_lock = threading.Lock()


def _iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


def to_dict(job: Job) -> dict:
    return {
        "project_id": job.project_id,
        "label": job.label,
        "status": job.status,
        "started_at": _iso(job.started_at),
        "finished_at": _iso(job.finished_at),
        "result": job.result,
        "error": job.error,
    }


def _expire(job: Job, now: float) -> None:
    if job.status == "running" and now - job.started_at > STUCK_AFTER_SECONDS:
        job.status = "error"
        job.error = "La generación tardó demasiado y se canceló. Tu levantamiento quedó guardado; intenta de nuevo."
        job.finished_at = now


def start(
    project_id: int, user_id: int, company_id: int, label: str, runner: Callable[[Session], dict]
) -> tuple[Job, bool]:
    """Arranca la generación. Devuelve (trabajo, nuevo). Si ya hay una en marcha para ese proyecto se une a ella
    en vez de crear otra cotización."""
    now = time.time()
    with _lock:
        existing = _jobs.get(project_id)
        if existing is not None:
            _expire(existing, now)
            if existing.status == "running":
                return existing, False
        job = Job(project_id=project_id, user_id=user_id, company_id=company_id, label=label, started_at=now)
        _jobs[project_id] = job
    threading.Thread(target=_work, args=(job, runner), name=f"generation-{project_id}", daemon=True).start()
    return job, True


def _work(job: Job, runner: Callable[[Session], dict]) -> None:
    from app.db.session import SessionLocal  # import tardío: evita ciclos al cargar la app

    db = SessionLocal(company_id=job.company_id)  # el hilo no hereda la empresa de la petición
    try:
        job.result = runner(db)
        job.status = "done"
    except HTTPException as exc:
        db.rollback()
        job.error = str(exc.detail)
        job.status = "error"
    except Exception:
        db.rollback()
        logger.exception("La generación de la cotización del proyecto %s falló", job.project_id)
        job.error = "La IA no pudo armar la cotización esta vez. Tu levantamiento quedó guardado; intenta de nuevo."
        job.status = "error"
    finally:
        db.close()
        job.finished_at = time.time()


def get(project_id: int) -> Job | None:
    now = time.time()
    with _lock:
        job = _jobs.get(project_id)
        if job is None:
            return None
        _expire(job, now)
        if job.status != "running" and job.finished_at and now - job.finished_at > KEEP_FINISHED_SECONDS:
            del _jobs[project_id]
            return None
        return job


def for_user(user_id: int) -> list[Job]:
    """Los trabajos de este usuario que siguen en marcha o terminaron hace menos de una hora."""
    with _lock:
        ids = [pid for pid, job in _jobs.items() if job.user_id == user_id]
    return [job for pid in ids if (job := get(pid)) is not None]


def forget(project_id: int) -> None:
    """Para las pruebas."""
    with _lock:
        _jobs.pop(project_id, None)


def reset() -> None:
    """Para las pruebas."""
    with _lock:
        _jobs.clear()
