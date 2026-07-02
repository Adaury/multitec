import uuid
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import get_current_user, require_role
from app.db.session import get_db
from app.models.logbook import LogEntry, LogEntryAsset
from app.models.user import User
from app.schemas.logbook import LogEntryAssetOut, LogEntryCreate, LogEntryOut

router = APIRouter(tags=["logbook"])

allowed_roles = require_role("admin", "oficina")

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/heic", "image/webp"}


@router.get("/api/projects/{project_id}/logbook", response_model=list[LogEntryOut])
def list_log_entries(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(LogEntry)
        .options(joinedload(LogEntry.assets))
        .filter(LogEntry.project_id == project_id)
        .order_by(LogEntry.entry_date.desc(), LogEntry.created_at.desc())
        .all()
    )


@router.post("/api/projects/{project_id}/logbook", response_model=LogEntryOut, status_code=status.HTTP_201_CREATED)
def create_log_entry(
    project_id: int,
    payload: LogEntryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = LogEntry(
        project_id=project_id,
        comment=payload.comment,
        entry_date=payload.entry_date or date.today(),
        responsible_id=current_user.id,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/api/logbook/{entry_id}/photos", response_model=LogEntryAssetOut, status_code=status.HTTP_201_CREATED)
async def upload_log_photo(
    entry_id: int,
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    entry = db.get(LogEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrada de bitácora no encontrada")
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {file.content_type}")

    settings = get_settings()
    entry_dir = Path(settings.upload_dir) / "logbook" / str(entry.id)
    entry_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = entry_dir / stored_name

    contents = await file.read()
    destination.write_bytes(contents)

    asset = LogEntryAsset(log_entry_id=entry.id, file_path=str(destination.as_posix()), description=description)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
