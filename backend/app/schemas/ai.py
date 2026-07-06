from pydantic import BaseModel

from app.schemas.budget import BudgetOut
from app.schemas.quote import QuoteOut


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
    warnings: list[str] = []


class AskRequest(BaseModel):
    project_id: int | None = None
    question: str


class AskResponse(BaseModel):
    answer: str
    projects: list[str] = []


class GenerateFromSurveyOut(BaseModel):
    """Resultado de generar Presupuesto + Cotización (+ borrador de Ingeniería, best
    effort) automáticamente a partir del levantamiento — § levantamiento inteligente."""

    budget: BudgetOut
    quote: QuoteOut
    engineering_drafted: bool
    warnings: list[str] = []
