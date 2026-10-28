import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.core.timeutil import today_dr
from app.db.session import get_db
from app.models.logbook import LogEntry, LogEntryAsset
from app.models.project import Project
from app.models.user import User
from app.schemas.logbook import LogEntryAssetOut, LogEntryCreate, LogEntryOut
from app.services.uploads import company_dir, enforce_matches_declared_type, read_upload, stored_extension

router = APIRouter(tags=["logbook"])

allowed_roles = require_role("admin", "oficina", "tecnico")

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
    current_user: User = Depends(allowed_roles),
):
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Proyecto no encontrado")

    entry = LogEntry(
        project_id=project_id,
        comment=payload.comment,
        entry_date=payload.entry_date or today_dr(),
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

    entry_dir = company_dir(db, "logbook", str(entry.id))
    entry_dir.mkdir(parents=True, exist_ok=True)

    extension = stored_extension(file.content_type)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = entry_dir / stored_name

    contents = await read_upload(file)
    enforce_matches_declared_type(contents, file.content_type)
    destination.write_bytes(contents)

    asset = LogEntryAsset(log_entry_id=entry.id, file_path=str(destination.as_posix()), description=description)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
