from pydantic import BaseModel


class ClientResult(BaseModel):
    id: int
    name: str
    company: str | None


class ProjectResult(BaseModel):
    id: int
    code: str
    client_name: str
    status: str


class TicketResult(BaseModel):
    id: int
    code: str
    problem: str
    project_id: int
    project_code: str


class SearchResults(BaseModel):
    clients: list[ClientResult]
    projects: list[ProjectResult]
    tickets: list[TicketResult]
