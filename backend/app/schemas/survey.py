from datetime import datetime

from pydantic import BaseModel, Field


class SurveyUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=10000)
    measurements: str | None = Field(default=None, max_length=10000)
    observations: str | None = Field(default=None, max_length=10000)


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
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    assets: list[SurveyAssetOut] = []

    class Config:
        from_attributes = True
