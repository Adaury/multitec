from datetime import datetime

from pydantic import BaseModel


class SurveyUpdate(BaseModel):
    notes: str | None = None
    measurements: str | None = None
    observations: str | None = None


class SurveyAssetOut(BaseModel):
    id: int
    kind: str
    file_path: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class SurveyOut(BaseModel):
    id: int
    project_id: int
    notes: str | None
    measurements: str | None
    observations: str | None
    ai_summary: str | None
    assets: list[SurveyAssetOut] = []

    class Config:
        from_attributes = True
