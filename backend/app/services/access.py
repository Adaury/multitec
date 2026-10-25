"""Qué puede ver cada técnico.

Admin y oficina ven todo el negocio. Un técnico ve solo lo suyo:
  - proyecto: lo creó, es el responsable, o tiene una visita o un ticket asignado;
  - cliente: lo creó, o es cliente de un proyecto suyo.

Las funciones *_scope devuelven una condición de SQLAlchemy para filtrar listados (None = sin límite).
`enforce_assignment_scope` valida las rutas con un id (project_id, client_id, ticket_id...) desde
get_current_user, así que cualquier endpoint nuevo con esos parámetros queda cubierto sin tocarlo.
Lo que no es suyo responde 404 (no 403) para no revelar que existe.
"""

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.logbook import LogEntry
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.user import User
from app.models.visit import Visit


def _restricted(user: User) -> bool:
    return user.role == "tecnico"


def project_scope(user: User):
    if not _restricted(user):
        return None
    uid = user.id
    return or_(
        Project.created_by == uid,
        Project.responsible_id == uid,
        Project.id.in_(select(Visit.project_id).where(Visit.technician_id == uid)),
        Project.id.in_(select(Ticket.project_id).where(Ticket.technician_id == uid)),
    )


def client_scope(user: User):
    if not _restricted(user):
        return None
    return or_(Client.created_by == user.id, Client.id.in_(select(Project.client_id).where(project_scope(user))))


def can_see_project(db: Session, user: User, project_id: int) -> bool:
    scope = project_scope(user)
    if scope is None:
        return True
    return db.query(Project.id).filter(Project.id == project_id, scope).first() is not None


def can_see_client(db: Session, user: User, client_id: int) -> bool:
    scope = client_scope(user)
    if scope is None:
        return True
    return db.query(Client.id).filter(Client.id == client_id, scope).first() is not None


def _not_found() -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No encontrado")


def enforce_assignment_scope(db: Session, user: User, path_params: dict) -> None:
    """Lanza 404 si la ruta apunta a algo que el técnico no puede ver. Si el objeto no existe no
    decide nada: lo responde el propio endpoint."""
    if not _restricted(user):
        return

    if "project_id" in path_params and not can_see_project(db, user, int(path_params["project_id"])):
        raise _not_found()

    if "client_id" in path_params:
        client_id = int(path_params["client_id"])
        exists = db.query(Client.id).filter(Client.id == client_id).first() is not None
        if exists and not can_see_client(db, user, client_id):
            raise _not_found()

    if "ticket_id" in path_params:
        ticket = db.get(Ticket, int(path_params["ticket_id"]))
        if ticket is not None and ticket.technician_id != user.id and not can_see_project(db, user, ticket.project_id):
            raise _not_found()

    if "visit_id" in path_params:
        visit = db.get(Visit, int(path_params["visit_id"]))
        if visit is not None and visit.technician_id != user.id and not can_see_project(db, user, visit.project_id):
            raise _not_found()

    if "entry_id" in path_params:
        entry = db.get(LogEntry, int(path_params["entry_id"]))
        if entry is not None and not can_see_project(db, user, entry.project_id):
            raise _not_found()
