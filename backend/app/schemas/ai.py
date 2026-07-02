from pydantic import BaseModel


class EngineeringDraftOut(BaseModel):
    recommended_equipment: str
    distribution: str
    conduits: str
    wiring: str
    technical_design: str
    observations: str


class BudgetSuggestionItem(BaseModel):
    product_id: int | None
    description: str
    quantity: float
    unit_price: float = 0


class BudgetSuggestionOut(BaseModel):
    items: list[BudgetSuggestionItem]


class AskRequest(BaseModel):
    project_id: int
    question: str


class AskResponse(BaseModel):
    answer: str
