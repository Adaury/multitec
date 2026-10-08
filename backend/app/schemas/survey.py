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


class VoiceSurveyOut(BaseModel):
    """Resultado de transcribir una nota de voz: el texto crudo más su reparto en los campos
    del levantamiento. No se guarda en el Survey — el técnico lo revisa antes de aplicarlo."""

    transcript: str
    notes: str
    measurements: str
    observations: str
    classified: bool


class VoiceFields(BaseModel):
    notes: str = Field(default="", max_length=10000)
    measurements: str = Field(default="", max_length=10000)
    observations: str = Field(default="", max_length=10000)


class VoiceFeedbackIn(BaseModel):
    """Lo que el frontend manda al aplicar un dictado: el texto, el reparto que hizo la IA y el
    que dejó el técnico tras revisarlo — de ahí se aprende (Motor 7)."""

    transcript: str = Field(min_length=1, max_length=20000)
    ai: VoiceFields
    final: VoiceFields
    classified: bool = True


class VoiceExampleOut(BaseModel):
    id: int
    project_id: int
    transcript: str
    ai_notes: str
    ai_measurements: str
    ai_observations: str
    final_notes: str
    final_measurements: str
    final_observations: str
    ai_classified: bool
    corrected: bool
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
