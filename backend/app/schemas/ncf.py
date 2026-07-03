from datetime import date, datetime

from pydantic import BaseModel, Field, model_validator

NCF_TYPES = ("B01", "B02", "B14", "B15")


class NcfSequenceCreate(BaseModel):
    ncf_type: str = Field(pattern=r"^B(01|02|14|15)$")
    description: str = Field(max_length=100)
    range_start: int = Field(gt=0)
    range_end: int = Field(gt=0)
    expires_at: date

    @model_validator(mode="after")
    def _check_range(self) -> "NcfSequenceCreate":
        if self.range_end < self.range_start:
            raise ValueError("range_end debe ser mayor o igual a range_start")
        return self


class NcfSequenceUpdate(BaseModel):
    active: bool


class NcfSequenceOut(BaseModel):
    id: int
    ncf_type: str
    description: str
    range_start: int
    range_end: int
    next_number: int
    expires_at: date
    active: bool
    created_by: int | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConvertToInvoiceRequest(BaseModel):
    ncf_type: str | None = Field(default=None, pattern=r"^B(01|02|14|15)$")
