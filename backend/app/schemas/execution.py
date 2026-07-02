from datetime import datetime

from pydantic import BaseModel


class ProjectStageOut(BaseModel):
    id: int
    name: str
    order: int
    completed: bool
    completed_at: datetime | None

    class Config:
        from_attributes = True


class ExecutionOut(BaseModel):
    stages: list[ProjectStageOut]
    progress_percent: float
