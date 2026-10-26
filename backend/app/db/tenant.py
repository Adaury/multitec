"""Aislamiento por empresa (multi-empresa en una sola base de datos).

La regla: toda tabla de negocio lleva `company_id` (se marca con `TenantMixin`) y la sesión de base de datos sabe
de qué empresa es (`session.info["company_id"]`). Con eso `TenantSession` (app/db/session.py) hace tres cosas
automáticamente, para que un filtro olvidado no pueda mostrar datos de otra empresa:

  1. a todo SELECT / UPDATE / DELETE del ORM le agrega `WHERE company_id = <la de la sesión>`;
  2. al insertar, pone el `company_id` de la sesión (y rechaza uno distinto);
  3. si la sesión no tiene empresa y toca una tabla de empresa, FALLA en vez de devolver todo.

La empresa vive en la sesión y no en un ContextVar a propósito: las dependencias síncronas de FastAPI corren en
hilos con una copia del contexto, y un ContextVar fijado ahí no llega al endpoint.
"""

from contextlib import contextmanager

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, Session, mapped_column


class TenantContextError(RuntimeError):
    """Se intentó leer o escribir datos de empresa sin saber de qué empresa. Es un error de programación o un
    intento de saltarse el aislamiento: nunca debe resolverse devolviendo todo."""


class TenantMixin:
    """Marca una tabla como "de una empresa". La columna es obligatoria; `TenantSession` la llena al insertar."""

    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), index=True)


def current_company_id(db: Session) -> int | None:
    return db.info.get("company_id")


@contextmanager
def tenant_bypass(db: Session):
    """Desactiva el filtro por empresa dentro del bloque. SOLO para: buscar al usuario al iniciar sesión, el panel
    de plataforma y scripts. Todo lo que se cree dentro debe llevar `company_id` explícito."""
    previous = db.info.get("bypass_tenant", False)
    db.info["bypass_tenant"] = True
    try:
        yield
    finally:
        db.info["bypass_tenant"] = previous
