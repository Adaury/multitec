from datetime import datetime

from pydantic import BaseModel, Field


class EngineeringUpdate(BaseModel):
    recommended_equipment: str | None = Field(default=None, max_length=10000)
    distribution: str | None = Field(default=None, max_length=10000)
    conduits: str | None = Field(default=None, max_length=10000)
    wiring: str | None = Field(default=None, max_length=10000)
    technical_design: str | None = Field(default=None, max_length=10000)
    observations: str | None = Field(default=None, max_length=10000)


class EngineeringOut(EngineeringUpdate):
    id: int
    project_id: int
    ai_generated: bool = False
    created_by: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
