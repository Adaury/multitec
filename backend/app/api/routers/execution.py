from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.execution import ProjectStage
from app.schemas.execution import ExecutionOut
from app.services.execution import stage_progress

router = APIRouter(prefix="/api/projects/{project_id}/execution", tags=["execution"])

allowed_roles = require_role("admin", "oficina")


def _get_stages(db: Session, project_id: int) -> list[ProjectStage]:
    return (
        db.query(ProjectStage)
        .filter(ProjectStage.project_id == project_id)
        .order_by(ProjectStage.order)
        .all()
    )


@router.get("", response_model=ExecutionOut)
def get_execution(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    stages = _get_stages(db, project_id)
    if not stages:
        raise HTTPException(status_code=404, detail="El proyecto no tiene etapas de ejecución")
    return ExecutionOut(stages=stages, progress_percent=stage_progress(stages))


@router.post("/advance", response_model=ExecutionOut)
def advance_stage(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    stages = _get_stages(db, project_id)
    next_stage = next((s for s in stages if not s.completed), None)
    if next_stage is None:
        raise HTTPException(status_code=400, detail="Todas las etapas ya están completas")
    next_stage.completed = True
    next_stage.completed_at = datetime.now(timezone.utc)
    db.commit()
    stages = _get_stages(db, project_id)
    return ExecutionOut(stages=stages, progress_percent=stage_progress(stages))


@router.post("/undo", response_model=ExecutionOut)
def undo_stage(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    stages = _get_stages(db, project_id)
    completed_stages = [s for s in stages if s.completed]
    if not completed_stages:
        raise HTTPException(status_code=400, detail="No hay etapas completadas para deshacer")
    last_stage = max(completed_stages, key=lambda s: s.order)
    last_stage.completed = False
    last_stage.completed_at = None
    db.commit()
    stages = _get_stages(db, project_id)
    return ExecutionOut(stages=stages, progress_percent=stage_progress(stages))
