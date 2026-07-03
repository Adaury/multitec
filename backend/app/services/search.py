from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.client import Client
from app.models.project import Project
from app.models.ticket import Ticket

RESULT_LIMIT = 8


def global_search(db: Session, q: str) -> dict:
    pattern = f"%{q}%"

    clients = (
        db.query(Client)
        .filter(or_(Client.name.ilike(pattern), Client.company.ilike(pattern), Client.rnc.ilike(pattern)))
        .order_by(Client.name)
        .limit(RESULT_LIMIT)
        .all()
    )

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
        .order_by(Project.created_at.desc())
        .limit(RESULT_LIMIT)
        .all()
    )

    tickets = (
        db.query(Ticket)
        .options(joinedload(Ticket.project))
        .filter(or_(Ticket.code.ilike(pattern), Ticket.problem.ilike(pattern)))
        .order_by(Ticket.created_at.desc())
        .limit(RESULT_LIMIT)
        .all()
    )

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
