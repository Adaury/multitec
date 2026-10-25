from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.project import Project
from app.models.ticket import Ticket
from app.models.user import User
from app.services.access import client_scope, project_scope

RESULT_LIMIT = 8


def global_search(db: Session, q: str, user: User | None = None) -> dict:
    """`user` limita los resultados a lo que ese usuario puede ver (técnico: solo lo suyo)."""
    pattern = f"%{q}%"
    clients_scope = client_scope(user) if user else None
    projects_scope = project_scope(user) if user else None

    clients = db.query(Client).filter(
        or_(Client.name.ilike(pattern), Client.company.ilike(pattern), Client.rnc.ilike(pattern))
    )
    if clients_scope is not None:
        clients = clients.filter(clients_scope)
    clients = clients.order_by(Client.name).limit(RESULT_LIMIT).all()

    projects = (
        db.query(Project)
        .options(joinedload(Project.client))
        .filter(
            or_(
                Project.code.ilike(pattern),
                Project.description.ilike(pattern),
                Project.client.has(Client.name.ilike(pattern)),
            )
        )
    )
    if projects_scope is not None:
        projects = projects.filter(projects_scope)
    projects = projects.order_by(Project.created_at.desc()).limit(RESULT_LIMIT).all()

    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.project))
        .filter(or_(Ticket.code.ilike(pattern), Ticket.problem.ilike(pattern)))
    )
    if projects_scope is not None:
        tickets = tickets.filter(
            or_(Ticket.technician_id == user.id, Ticket.project_id.in_(select(Project.id).where(projects_scope)))
        )
    tickets = tickets.order_by(Ticket.created_at.desc()).limit(RESULT_LIMIT).all()

    return {
        "clients": [{"id": c.id, "name": c.name, "company": c.company} for c in clients],
        "projects": [
            {"id": p.id, "code": p.code, "client_name": p.client.name, "status": p.status} for p in projects
        ],
        "tickets": [
            {"id": t.id, "code": t.code, "problem": t.problem, "project_id": t.project_id, "project_code": t.project.code}
            for t in tickets
        ],
    }
