from datetime import datetime

from pydantic import BaseModel


class AIFeedbackEventOut(BaseModel):
    id: int
    project_id: int
    entity_type: str
    origin: str
    product_id: int | None
    field_changed: str | None
    old_value: str | None
    new_value: str | None
    created_at: datetime

    class Config:
        from_attributes = True
