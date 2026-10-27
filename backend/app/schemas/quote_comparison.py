from datetime import datetime

from pydantic import BaseModel, Field


class ComparisonItem(BaseModel):
    description: str = Field(min_length=1, max_length=300)
    quantity: float = Field(gt=0)
    unit_price: float = Field(ge=0)


class ComparisonUpdate(BaseModel):
    """Oficina corrige lo que la IA leyó (o cambia contra qué cotización se compara)."""

    label: str | None = Field(default=None, min_length=1, max_length=120)
    quote_id: int | None = None
    items: list[ComparisonItem] | None = Field(default=None, max_length=200)
    total: float | None = Field(default=None, ge=0)


class ComparisonSummary(BaseModel):
    id: int
    label: str
    filename: str | None
    quote_id: int | None
    created_at: datetime
    lines: int


class MatchedLine(BaseModel):
    external: ComparisonItem
    ours: ComparisonItem
    same_quantity: bool
    price: str  # igual | mas_caro | mas_barato (la cotización ajena frente a la propia)
    price_diff_pct: float
    status: str  # igual | diferente


class CoverageRow(BaseModel):
    kind: str
    label: str
    marked: int
    external: float
    ours: float
    external_status: str  # ok | falta | sobra
    ours_status: str


class ComparisonTotals(BaseModel):
    external_subtotal: float
    external_total: float | None
    our_subtotal: float | None
    our_total: float | None
    our_code: str | None


class ComparisonOut(BaseModel):
    id: int
    project_id: int
    label: str
    filename: str | None
    file_path: str | None
    quote_id: int | None
    created_at: datetime
    items: list[ComparisonItem]
    total: float | None
    matched: list[MatchedLine]
    only_external: list[ComparisonItem]
    only_ours: list[ComparisonItem]
    coverage: list[CoverageRow]
    totals: ComparisonTotals
