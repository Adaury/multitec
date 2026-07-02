import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.survey import Survey, SurveyAsset
from app.schemas.survey import SurveyAssetOut, SurveyOut, SurveyUpdate

router = APIRouter(prefix="/api/projects/{project_id}/survey", tags=["surveys"])

allowed_roles = require_role("admin", "oficina")

ALLOWED_KINDS = {"photo", "audio"}
ALLOWED_CONTENT_TYPES = {
    "photo": {"image/jpeg", "image/png", "image/heic", "image/webp"},
    "audio": {"audio/mpeg", "audio/mp4", "audio/m4a", "audio/wav", "audio/webm", "audio/x-m4a"},
}


def _get_survey(db: Session, project_id: int) -> Survey:
    survey = (
        db.query(Survey)
        .options(joinedload(Survey.assets))
        .filter(Survey.project_id == project_id)
        .one_or_none()
    )
    if survey is None:
        raise HTTPException(status_code=404, detail="Levantamiento no encontrado")
    return survey


@router.get("", response_model=SurveyOut)
def get_survey(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return _get_survey(db, project_id)


@router.put("", response_model=SurveyOut)
def update_survey(project_id: int, payload: SurveyUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    survey = _get_survey(db, project_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(survey, field, value)
    db.commit()
    db.refresh(survey)
    return survey


@router.post("/assets", response_model=SurveyAssetOut, status_code=status.HTTP_201_CREATED)
async def upload_asset(
    project_id: int,
    kind: str = Form(...),
    description: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    if kind not in ALLOWED_KINDS:
        raise HTTPException(status_code=400, detail="kind debe ser 'photo' o 'audio'")
    if file.content_type not in ALLOWED_CONTENT_TYPES[kind]:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido para {kind}: {file.content_type}")

    survey = _get_survey(db, project_id)

    settings = get_settings()
    survey_dir = Path(settings.upload_dir) / "surveys" / str(survey.id)
    survey_dir.mkdir(parents=True, exist_ok=True)

    extension = Path(file.filename or "").suffix
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = survey_dir / stored_name

    contents = await file.read()
    destination.write_bytes(contents)

    asset = SurveyAsset(
        survey_id=survey.id,
        kind=kind,
        file_path=str(destination.as_posix()),
        description=description,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
