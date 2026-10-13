from datetime import date, time

from pydantic import BaseModel, Field


class TodayVisit(BaseModel):
    id: int
    project_id: int
    project_code: str
    client_name: str
    scheduled_time: time | None
    address: str | None
    location_url: str | None
    phone: str | None
    notes: str | None


class TodayProject(BaseModel):
    """Un proyecto que pide acción hoy (levantamiento listo para cotizar, por ejemplo)."""

    project_id: int
    project_code: str
    client_name: str
    survey_type: str | None
    status: str | None = None


class TodayQuote(BaseModel):
    quote_id: int
    code: str
    project_id: int
    client_name: str
    total: float
    days_pending: int


class TodayTicket(BaseModel):
    id: int
    code: str
    project_id: int
    client_name: str
    problem: str
    status: str


class TodayOut(BaseModel):
    """Lo que el asistente le dice al usuario al abrir la app: qué hay para hoy."""

    today: date
    visits: list[TodayVisit]
    ready_to_quote: list[TodayProject]
    quotes_waiting: list[TodayQuote]
    tickets: list[TodayTicket]
    # Los últimos proyectos abiertos del usuario, para "continuar donde lo dejé".
    continue_projects: list[TodayProject] = []


class TalkIn(BaseModel):
    """Lo que el técnico le dijo al asistente (dictado o escrito)."""

    text: str = Field(max_length=600)
    survey_types: list[str] = Field(default_factory=list, max_length=30)


class TalkOut(BaseModel):
    # new_survey | open_project | ask_project | agenda | quotes | tickets | none | unknown
    intent: str
    reply: str
    navigate_to: str | None = None
    client_name: str = ""
    client_id: int | None = None
    phone: str = ""
    survey_type: str = ""
    ai_used: bool = False
    # Lo que Whisper entendió del audio (solo en /listen), para mostrárselo al técnico.
    heard: str = ""
