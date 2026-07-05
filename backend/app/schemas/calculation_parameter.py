from datetime import datetime

from pydantic import BaseModel, Field


class CalculationParameterUpsert(BaseModel):
    value: float
    description: str | None = Field(default=None, max_length=200)


class CalculationParameterOut(BaseModel):
    key: str
    value: float
    description: str | None
    is_default: bool
    updated_at: datetime | None = None
