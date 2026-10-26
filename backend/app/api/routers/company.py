from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.company_profile import CompanyProfile
from app.models.user import User
from app.schemas.company import CompanyOut, CompanyUpdate
from app.services import company as company_service
from app.services.audit import audit
from app.services.uploads import enforce_matches_declared_type, read_upload

router = APIRouter(prefix="/api/company", tags=["company"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


def _out(db: Session) -> CompanyOut:
    info = company_service.get_company(db)
    has_logo = bool(info.logo_path) and Path(info.logo_path).is_file()
    return CompanyOut(**{f: getattr(info, f) for f in company_service.FIELDS}, has_logo=has_logo)


@router.get("", response_model=CompanyOut)
def get_company(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return _out(db)


@router.put("", response_model=CompanyOut)
def update_company(
    request: Request, payload: CompanyUpdate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    profile = company_service.get_profile(db) or CompanyProfile()
    changed = []
    for field in company_service.FIELDS:
        value = getattr(payload, field)
        new = value.strip() if value and value.strip() else None
        if getattr(profile, field, None) != new:
            changed.append(field)  # solo los nombres de los campos: el RNC y las cuentas no se copian a la bitácora
        setattr(profile, field, new)
    db.add(profile)
    if changed:
        audit(db, "company_updated", user=current_user, entity="company", detail={"campos": changed}, request=request)
    db.commit()
    return _out(db)


@router.post("/logo", response_model=CompanyOut)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(admin_only)):
    base_type = (file.content_type or "").split(";")[0].strip().lower()
    if base_type not in company_service.LOGO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="El logo debe ser una imagen PNG, JPG o WebP.")
    contents = await read_upload(file)
    enforce_matches_declared_type(contents, file.content_type)
    company_service.save_logo(db, contents)
    return _out(db)


@router.delete("/logo", response_model=CompanyOut)
def delete_logo(db: Session = Depends(get_db), _=Depends(admin_only)):
    company_service.remove_logo(db)
    return _out(db)


@router.get("/logo")
def get_logo(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    path = company_service.get_company(db).logo_path
    if not path or not Path(path).is_file():
        raise HTTPException(status_code=404, detail="Todavía no hay logo")
    return FileResponse(path, headers={"Cache-Control": "no-cache"})
