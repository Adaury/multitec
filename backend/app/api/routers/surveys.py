import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import require_role
from app.db.session import get_db
from app.models.survey import Survey, SurveyAsset, SurveyMarker
from app.schemas.survey import SurveyAssetOut, SurveyMarkersUpdate, SurveyOut, SurveyUpdate
from app.services.survey_points import POINT_KIND_KEYS
from app.services.uploads import company_dir, enforce_matches_declared_type, read_upload, stored_extension

router = APIRouter(prefix="/api/projects/{project_id}/survey", tags=["surveys"])

allowed_roles = require_role("admin", "oficina", "tecnico")

ALLOWED_KINDS = {"photo", "audio"}
ALLOWED_CONTENT_TYPES = {
    "photo": {"image/jpeg", "image/png", "image/heic", "image/webp"},
    "audio": {"audio/mpeg", "audio/mp4", "audio/m4a", "audio/wav", "audio/webm", "audio/x-m4a"},
}


def _get_survey(db: Session, project_id: int) -> Survey:
    survey = (
        db.query(Survey)
        .options(joinedload(Survey.assets).joinedload(SurveyAsset.markers))
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
    # MediaRecorder en Chrome/Edge etiqueta el audio "audio/webm;codecs=opus" — se compara
    # solo el tipo base, sin los parámetros.
    base_type = (file.content_type or "").split(";")[0].strip().lower()
    if base_type not in ALLOWED_CONTENT_TYPES[kind]:
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido para {kind}: {file.content_type}")

    survey = _get_survey(db, project_id)

    survey_dir = company_dir(db, "surveys", str(survey.id))
    survey_dir.mkdir(parents=True, exist_ok=True)

    extension = stored_extension(file.content_type)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    destination = survey_dir / stored_name

    contents = await read_upload(file)
    enforce_matches_declared_type(contents, file.content_type)
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


@router.put("/assets/{asset_id}/markers", response_model=SurveyAssetOut)
def update_markers(
    project_id: int,
    asset_id: int,
    payload: SurveyMarkersUpdate,
    db: Session = Depends(get_db),
    _=Depends(allowed_roles),
):
    """Reemplaza los marcadores de una foto y renumera todo el levantamiento de corrido
    (1, 2, 3...) según el orden de las fotos, para que la numeración que ve el cliente en el
    anexo de la cotización no tenga huecos."""
    survey = _get_survey(db, project_id)
    asset = next((a for a in survey.assets if a.id == asset_id), None)
    if asset is None or asset.kind != "photo":
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    asset.markers.clear()
    db.flush()
    for item in payload.markers:
        kind = item.kind if item.kind in POINT_KIND_KEYS else None  # un tipo desconocido se ignora y se deduce del nombre
        asset.markers.append(
            SurveyMarker(x=item.x, y=item.y, label=(item.label or "").strip() or None, kind=kind, number=0)
        )
    db.flush()

    number = 1
    for photo in sorted(survey.assets, key=lambda a: a.id):
        for marker in sorted(photo.markers, key=lambda m: m.id):
            marker.number = number
            number += 1
    db.commit()
    db.refresh(asset)
    return asset


@router.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_asset(project_id: int, asset_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    survey = _get_survey(db, project_id)
    asset = next((a for a in survey.assets if a.id == asset_id), None)
    if asset is None:
        raise HTTPException(status_code=404, detail="Archivo no encontrado")

    file_path = Path(asset.file_path)
    db.delete(asset)
    db.commit()
    file_path.unlink(missing_ok=True)
