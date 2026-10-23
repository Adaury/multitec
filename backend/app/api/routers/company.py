from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.company_profile import CompanyProfile
from app.schemas.company import CompanyOut, CompanyUpdate
from app.services import company as company_service
from app.services.uploads import enforce_upload_size

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
def update_company(payload: CompanyUpdate, db: Session = Depends(get_db), _=Depends(admin_only)):
    profile = company_service.get_profile(db) or CompanyProfile(id=1)
    for field in company_service.FIELDS:
        value = getattr(payload, field)
        setattr(profile, field, value.strip() if value and value.strip() else None)
    db.add(profile)
    db.commit()
    return _out(db)


@router.post("/logo", response_model=CompanyOut)
async def upload_logo(file: UploadFile = File(...), db: Session = Depends(get_db), _=Depends(admin_only)):
    base_type = (file.content_type or "").split(";")[0].strip().lower()
    if base_type not in company_service.LOGO_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="El logo debe ser una imagen PNG, JPG o WebP.")
    contents = await file.read()
    enforce_upload_size(contents)
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
