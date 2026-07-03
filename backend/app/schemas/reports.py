from pydantic import BaseModel


class ProjectsByStatus(BaseModel):
    status: str
    count: int


class MonthlyInvoicing(BaseModel):
    month: str
    total: float


class TicketsByTechnician(BaseModel):
    technician: str
    count: int


class DashboardSummary(BaseModel):
    projects_by_status: list[ProjectsByStatus]
    monthly_invoicing: list[MonthlyInvoicing]
    quotes_pending: int
    open_tickets_by_technician: list[TicketsByTechnician]
    open_tickets_total: int
