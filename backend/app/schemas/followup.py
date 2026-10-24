from datetime import date

from pydantic import BaseModel


class FollowupInvoice(BaseModel):
    invoice_id: int
    project_id: int
    code: str
    ncf: str | None
    client_name: str
    client_phone: str | None
    total: float
    issued_on: date
    due_on: date
    # Positivo = días de atraso; cero o negativo = faltan (o vence hoy).
    days_overdue: int
    overdue: bool
    message: str
    whatsapp_url: str | None


class FollowupQuote(BaseModel):
    quote_id: int
    project_id: int
    code: str
    client_name: str
    client_phone: str | None
    total: float
    sent_on: date
    days_waiting: int
    # Pasó el plazo de QUOTE_STALE_DAYS: la cotización se archiva sola si nadie responde.
    stale: bool
    message: str
    whatsapp_url: str | None


class FollowupsOut(BaseModel):
    receivables_total: float
    overdue_total: float
    overdue_count: int
    receivables: list[FollowupInvoice]
    quotes: list[FollowupQuote]
