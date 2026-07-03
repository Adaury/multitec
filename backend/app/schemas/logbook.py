from datetime import date, datetime

from pydantic import BaseModel, Field


class LogEntryCreate(BaseModel):
    comment: str = Field(max_length=5000)
    entry_date: date | None = None


class LogEntryAssetOut(BaseModel):
    id: int
    file_path: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class LogEntryOut(BaseModel):
    id: int
    project_id: int
    comment: str
    entry_date: date
    responsible_id: int | None
    created_at: datetime
    assets: list[LogEntryAssetOut] = []

    class Config:
        from_attributes = True
