from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.extension import EXTENSION_STATUSES, Extension
from app.models.quote import Quote
from app.schemas.extension import ExtensionCreate, ExtensionOut, ExtensionStatusUpdate
from app.services.code_generator import next_code

router = APIRouter(tags=["extensions"])

allowed_roles = require_role("admin", "oficina")


@router.get("/api/projects/{project_id}/extensions", response_model=list[ExtensionOut])
def list_extensions(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Extension)
        .filter(Extension.project_id == project_id)
        .order_by(Extension.created_at.desc())
        .all()
    )


@router.post("/api/projects/{project_id}/extensions", response_model=ExtensionOut, status_code=status.HTTP_201_CREATED)
def create_extension(project_id: int, payload: ExtensionCreate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    if payload.quote_id is not None:
        quote = db.get(Quote, payload.quote_id)
        if quote is None or quote.project_id != project_id:
            raise HTTPException(status_code=400, detail="La cotización debe pertenecer al mismo proyecto")

    code = next_code(db, "AMP")
    data = payload.model_dump(exclude_unset=True)
    extension = Extension(code=code, project_id=project_id, **data)
    db.add(extension)
    db.commit()
    db.refresh(extension)
    return extension


@router.put("/api/extensions/{extension_id}/status", response_model=ExtensionOut)
def update_extension_status(
    extension_id: int, payload: ExtensionStatusUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    if payload.status not in EXTENSION_STATUSES:
        raise HTTPException(status_code=400, detail=f"Estado inválido: {payload.status}")
    extension = db.get(Extension, extension_id)
    if extension is None:
        raise HTTPException(status_code=404, detail="Ampliación no encontrada")
    extension.status = payload.status
    db.commit()
    db.refresh(extension)
    return extension
