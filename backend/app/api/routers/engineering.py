from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_engine.learning import record_engineering_edit_feedback
from app.core.security import require_role
from app.db.session import get_db
from app.models.engineering import Engineering
from app.models.project import Project
from app.models.user import User
from app.schemas.engineering import EngineeringOut, EngineeringUpdate

router = APIRouter(prefix="/api/projects/{project_id}/engineering", tags=["engineering"])

allowed_roles = require_role("admin", "oficina", "tecnico")


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
    current_user: User = Depends(allowed_roles),
):
    engineering = db.query(Engineering).filter(Engineering.project_id == project_id).one_or_none()
    if engineering is None:
        # Proyecto sin ingeniería todavía (no se generó el borrador): guardar la crea, en vez de
        # responder 404 y perder lo que se escribió a mano.
        if db.get(Project, project_id) is None:
            raise HTTPException(status_code=404, detail="Proyecto no encontrado")
        engineering = Engineering(project_id=project_id, created_by=current_user.id)
        db.add(engineering)

    new_values = payload.model_dump(exclude_unset=True)
    record_engineering_edit_feedback(db, project_id, engineering, new_values)
    for field, value in new_values.items():
        setattr(engineering, field, value)
    db.commit()
    db.refresh(engineering)
    return engineering
