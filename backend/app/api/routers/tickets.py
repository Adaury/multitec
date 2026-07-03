import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.ticket import TICKET_STATUSES, Ticket, TicketAsset, TicketHistory
from app.models.user import User
from app.schemas.ticket import TicketAssetOut, TicketCreate, TicketHistoryOut, TicketOut, TicketUpdate
from app.services.code_generator import next_code
from app.services.notifications import notify_ticket_assigned
from app.services.uploads import enforce_upload_size

router = APIRouter(tags=["tickets"])

allowed_roles = require_role("admin", "oficina", "tecnico")

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}


def _get_ticket(db: Session, ticket_id: int) -> Ticket:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    return ticket


@router.get("/api/projects/{project_id}/tickets", response_model=list[TicketOut])
def list_tickets(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Ticket)
        .options(joinedload(Ticket.assets))
        .filter(Ticket.project_id == project_id)
        .order_by(Ticket.created_at.desc())
        .all()
    )


@router.post("/api/projects/{project_id}/tickets", response_model=TicketOut, status_code=status.HTTP_201_CREATED)
def create_ticket(
    project_id: int, payload: TicketCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    code = next_code(db, "TKT")
    ticket = Ticket(
        code=code,
        project_id=project_id,
        problem=payload.problem,
        technician_id=payload.technician_id,
        status="abierto",
        created_by=current_user.id,
    )
    db.add(ticket)
    db.flush()
    db.add(TicketHistory(ticket_id=ticket.id, action="abierto"))
    db.commit()
    db.refresh(ticket)
    notify_ticket_assigned(db, ticket)
    return ticket


@router.put("/api/tickets/{ticket_id}", response_model=TicketOut)
def update_ticket(ticket_id: int, payload: TicketUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    ticket = _get_ticket(db, ticket_id)
    data = payload.model_dump(exclude_unset=True)
    previous_technician_id = ticket.technician_id

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
    if ticket.technician_id is not None and ticket.technician_id != previous_technician_id:
        notify_ticket_assigned(db, ticket)
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


@router.post("/api/tickets/{ticket_id}/photos", response_model=TicketAssetOut, status_code=status.HTTP_201_CREATED)
async def upload_ticket_photo(
    ticket_id: int,
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    ticket = _get_ticket(db, ticket_id)
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {file.content_type}")

    settings = get_settings()
    ticket_dir = Path(settings.upload_dir) / "tickets" / str(ticket.id)
    ticket_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = ticket_dir / stored_name

    contents = await file.read()
    enforce_upload_size(contents)
    destination.write_bytes(contents)

    asset = TicketAsset(ticket_id=ticket.id, file_path=str(destination.as_posix()), description=description)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/api/tickets/{ticket_id}/photos/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ticket_photo(ticket_id: int, asset_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    ticket = _get_ticket(db, ticket_id)
    asset = next((a for a in ticket.assets if a.id == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_path = Path(asset.file_path)
    db.delete(asset)
    db.commit()
    file_path.unlink(missing_ok=True)
