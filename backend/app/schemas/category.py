from datetime import datetime

from pydantic import BaseModel, Field


class CategoryCreate(BaseModel):
    name: str = Field(max_length=120)
    parent_id: int | None = None
    code_prefix: str | None = Field(default=None, max_length=10)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120)
    parent_id: int | None = None
    code_prefix: str | None = Field(default=None, max_length=10)


class CategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    code_prefix: str | None
    parent_id: int | None
    created_at: datetime | None = None

    class Config:
        from_attributes = True
