from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.ticket import TICKET_STATUSES, Ticket, TicketHistory
from app.schemas.ticket import TicketCreate, TicketHistoryOut, TicketOut, TicketUpdate
from app.services.code_generator import next_code

router = APIRouter(tags=["tickets"])

allowed_roles = require_role("admin", "oficina")


def _get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.get("/api/projects/{project_id}/tickets", response_model=list[TicketOut])
def list_tickets(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Ticket)
        .filter(Ticket.project_id == project_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


@router.post("/api/projects/{project_id}/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(project_id: int, payload: TicketCreate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    code = next_code(db, "TKT")
    ticket = Ticket(
        code=code,
        project_id=project_id,
        problem=payload.problem,
        technician_id=payload.technician_id,
        status="abierto",
    )
    db.add(ticket)
    db.flush()
    db.add(TicketHistory(ticket_id=ticket.id, action="abierto"))
    db.commit()
    db.refresh(ticket)
    return ticket


@router.put("/api/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    ticket = _get_ticket(db, ticket_id)
    data = payload.model_dump(exclude_unset=True)

    if "status" in data:
        if data["status"] not in TICKET_STATUSES:
            raise HTTPException(status_code=400, detail=f"Estado inválido: {data['status']}")
        if data["status"] != ticket.status:
            db.add(TicketHistory(ticket_id=ticket.id, action=data["status"]))
            if data["status"] in ("resuelto", "cerrado"):
                ticket.resolved_at = datetime.now(timezone.utc)

    for field, value in data.items():
        setattr(ticket, field, value)

    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/api/tickets/{ticket_id}/history", response_model=list[TicketHistoryOut])
def get_ticket_history(ticket_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    _get_ticket(db, ticket_id)
    return (
        db.query(TicketHistory)
        .filter(TicketHistory.ticket_id == ticket_id)
        .order_by(TicketHistory.created_at)
        .all()
    )
