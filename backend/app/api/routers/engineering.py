from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.engineering import Engineering
from app.schemas.engineering import EngineeringOut, EngineeringUpdate

router = APIRouter(prefix="/api/projects/{project_id}/engineering", tags=["engineering"])

allowed_roles = require_role("admin", "oficina")


@router.get("", response_model=EngineeringOut)
def get_engineering(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    engineering = db.query(Engineering).filter(Engineering.project_id == project_id).one_or_none()
    if engineering is None:
        raise HTTPException(status_code=404, detail="Ingeniería no encontrada")
    return engineering


@router.put("", response_model=EngineeringOut)
def update_engineering(
    project_id: int,
    payload: EngineeringUpdate,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    engineering = db.query(Engineering).filter(Engineering.project_id == project_id).one_or_none()
    if engineering is None:
        raise HTTPException(status_code=404, detail="Ingeniería no encontrada")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(engineering, field, value)
    db.commit()
    db.refresh(engineering)
    return engineering
