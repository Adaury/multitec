from pydantic import BaseModel


class EngineeringUpdate(BaseModel):
    recommended_equipment: str | None = None
    distribution: str | None = None
    conduits: str | None = None
    wiring: str | None = None
    technical_design: str | None = None
    observations: str | None = None


class EngineeringOut(EngineeringUpdate):
    id: int
    project_id: int

    class Config:
        from_attributes = True
