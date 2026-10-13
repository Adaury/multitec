import json
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.ai_engine.conversation import understand
from app.ai_engine.transcription import CONVERSATION_PROMPT, transcribe_audio
from app.core.security import require_role
from app.core.timeutil import to_local, today_dr
from app.db.session import get_db
from app.models.client import Client
from app.models.project import Project
from app.models.quote import Quote
from app.models.survey import Survey
from app.models.ticket import Ticket
from app.models.user import User
from app.models.visit import Visit
from app.schemas.assistant import TalkIn, TalkOut, TodayOut
from app.services.reports import OPEN_TICKET_STATUSES
from app.services.uploads import enforce_upload_size

router = APIRouter(prefix="/api/assistant", tags=["assistant"])

allowed_roles = require_role("admin", "oficina", "tecnico")

# Tope por lista: es un resumen para decidir qué hacer ahora, no un listado completo.
LIMIT = 5


def _mine(user: User):
    """Un técnico ve lo suyo (responsable o quien lo creó); admin y oficina ven todo el negocio."""
    if user.role == "tecnico":
        return or_(Project.responsible_id == user.id, Project.created_by == user.id)
    return None


@router.get("/today", response_model=TodayOut)
def get_today(db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    """Resumen del día para el asistente: visitas de hoy, levantamientos listos para cotizar,
    cotizaciones esperando respuesta y tickets abiertos. Solo lectura, sin IA: debe responder al
    instante y no depender de que el modelo esté cargado."""
    return build_today(db, current_user)


def build_today(db: Session, current_user: User) -> dict:
    today = today_dr()
    mine = _mine(current_user)

    visit_query = (
        db.query(Visit)
        .options(joinedload(Visit.project).joinedload(Project.client))
        .filter(Visit.scheduled_date == today, Visit.status == "programada")
    )
    if current_user.role == "tecnico":
        visit_query = visit_query.filter(Visit.technician_id == current_user.id)
    visits = [
        {
            "id": v.id,
            "project_id": v.project_id,
            "project_code": v.project.code,
            "client_name": v.project.client.name,
            "scheduled_time": v.scheduled_time,
            "address": v.client_address,
            "location_url": v.client_location_url,
            "phone": v.client_phone,
            "notes": v.notes,
        }
        for v in visit_query.order_by(Visit.scheduled_time.is_(None), Visit.scheduled_time).limit(LIMIT).all()
    ]

    # Levantamiento con notas y sin ninguna cotización todavía: lo siguiente es cotizarlo.
    ready_query = (
        db.query(Project)
        .options(joinedload(Project.client))
        .join(Survey, Survey.project_id == Project.id)
        .filter(
            Project.status == "levantamiento",
            func.length(func.trim(func.coalesce(Survey.notes, ""))) > 0,
            ~Project.quotes.any(),
        )
    )
    if mine is not None:
        ready_query = ready_query.filter(mine)
    ready = [
        {
            "project_id": p.id,
            "project_code": p.code,
            "client_name": p.client.name,
            "survey_type": p.survey_type,
        }
        for p in ready_query.order_by(Project.created_at.desc()).limit(LIMIT).all()
    ]

    quote_query = (
        db.query(Quote)
        .join(Project, Project.id == Quote.project_id)
        .options(joinedload(Quote.project).joinedload(Project.client))
        .filter(Quote.status == "pendiente")
    )
    if mine is not None:
        quote_query = quote_query.filter(mine)
    waiting = [
        {
            "quote_id": q.id,
            "code": q.code,
            "project_id": q.project_id,
            "client_name": q.project.client.name,
            "total": float(q.total),
            "days_pending": max(0, (today - to_local(q.created_at).date()).days),
        }
        for q in quote_query.order_by(Quote.created_at).limit(LIMIT).all()
    ]

    ticket_query = (
        db.query(Ticket)
        .options(joinedload(Ticket.project).joinedload(Project.client))
        .filter(Ticket.status.in_(OPEN_TICKET_STATUSES))
    )
    # El técnico ve los que tiene asignados; admin y oficina, todos los abiertos del negocio.
    if current_user.role == "tecnico":
        ticket_query = ticket_query.filter(Ticket.technician_id == current_user.id)
    tickets = [
        {
            "id": t.id,
            "code": t.code,
            "project_id": t.project_id,
            "client_name": t.project.client.name,
            "problem": t.problem,
            "status": t.status,
        }
        for t in ticket_query.order_by(Ticket.created_at).limit(LIMIT).all()
    ]

    recent_query = db.query(Project).options(joinedload(Project.client)).filter(Project.status != "cerrado")
    if mine is not None:
        recent_query = recent_query.filter(mine)
    recent = [
        {
            "project_id": p.id,
            "project_code": p.code,
            "client_name": p.client.name,
            "survey_type": p.survey_type,
            "status": p.status,
        }
        for p in recent_query.order_by(func.coalesce(Project.updated_at, Project.created_at).desc()).limit(3).all()
    ]

    return {
        "today": today,
        "visits": visits,
        "ready_to_quote": ready,
        "quotes_waiting": waiting,
        "tickets": tickets,
        "continue_projects": recent,
    }


def _count_phrase(count: int, one: str, many: str) -> str:
    return f"{count} {one if count == 1 else many}"


def _agenda_sentence(today: dict) -> str:
    parts = []
    if today["visits"]:
        parts.append(_count_phrase(len(today["visits"]), "visita", "visitas"))
    if today["ready_to_quote"]:
        parts.append(
            _count_phrase(len(today["ready_to_quote"]), "levantamiento listo para cotizar", "levantamientos listos para cotizar")
        )
    if today["quotes_waiting"]:
        parts.append(
            _count_phrase(len(today["quotes_waiting"]), "cotización esperando respuesta", "cotizaciones esperando respuesta")
        )
    if today["tickets"]:
        parts.append(_count_phrase(len(today["tickets"]), "ticket abierto", "tickets abiertos"))
    if not parts:
        return "Hoy no tienes visitas ni pendientes urgentes."
    if len(parts) == 1:
        return f"Hoy tienes {parts[0]}."
    return f"Hoy tienes {', '.join(parts[:-1])} y {parts[-1]}."


UNKNOWN_REPLY = (
    "No te entendí bien. Puedes decirme, por ejemplo: «un levantamiento de cámaras para Juan Pérez», "
    "«continuar con Ferretería López» o «qué tengo hoy»."
)


@router.post("/talk", response_model=TalkOut)
def talk(payload: TalkIn, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    """Un turno de la conversación del Inicio: recibe lo que el técnico dijo y devuelve qué
    responderle y a dónde llevarlo. No crea ni modifica nada: solo interpreta y dirige."""
    return _respond(db, current_user, payload.text, payload.survey_types)


def _respond(db: Session, current_user: User, text: str, survey_types: list[str]) -> dict:
    mine = _mine(current_user)
    project_query = db.query(Project).options(joinedload(Project.client)).filter(Project.status != "cerrado")
    if mine is not None:
        project_query = project_query.filter(mine)
    projects = [
        {"project_id": p.id, "project_code": p.code, "client_name": p.client.name}
        for p in project_query.order_by(func.coalesce(Project.updated_at, Project.created_at).desc()).limit(300).all()
    ]

    understood = understand(text, survey_types, projects)
    intent = understood["intent"]
    out = {
        "intent": intent or "unknown",
        "reply": UNKNOWN_REPLY,
        "navigate_to": None,
        "client_name": understood["client_name"],
        "client_id": None,
        "phone": understood["phone"],
        "survey_type": understood["survey_type"],
        "ai_used": understood["ai_used"],
    }

    if intent == "new_survey":
        name = understood["client_name"]
        kind = f" de {understood['survey_type']}" if understood["survey_type"] else ""
        existing = db.query(Client).filter(func.lower(Client.name) == name.lower()).first() if name else None
        if existing is not None:
            out["client_id"] = existing.id
            out["client_name"] = existing.name
            out["reply"] = f"Perfecto. Vamos con el levantamiento{kind} para {existing.name}, que ya es cliente."
        elif name:
            out["reply"] = f"Perfecto. Vamos con el levantamiento{kind} para {name}. Te pido lo que falta."
        else:
            out["reply"] = f"Perfecto, empecemos un levantamiento{kind}. Dime el nombre del cliente y su teléfono."
        out["navigate_to"] = "/nuevo"
    elif intent == "open_project":
        project = understood["project"]
        if project is None:
            out["intent"] = "ask_project"
            out["reply"] = "No encontré un proyecto abierto con ese nombre. ¿De qué cliente es?"
        else:
            out["client_name"] = project["client_name"]
            out["reply"] = f"Abro el proyecto de {project['client_name']}, {project['project_code']}."
            out["navigate_to"] = f"/proyectos/{project['project_id']}"
    elif intent == "agenda":
        today = build_today(db, current_user)
        sentence = _agenda_sentence(today)
        first = today["visits"][0] if today["visits"] else None
        if first is not None:
            when = f" a las {first['scheduled_time'].strftime('%H:%M')}" if first["scheduled_time"] else ""
            sentence += f" La primera visita es con {first['client_name']}{when}."
        has_work = any(today[key] for key in ("visits", "ready_to_quote", "quotes_waiting", "tickets"))
        out["reply"] = sentence + (" ¿Con cuál empezamos?" if has_work else " ¿Qué quieres hacer?")
    elif intent == "quotes":
        out["reply"] = "Te muestro las cotizaciones."
        out["navigate_to"] = "/cotizaciones"
    elif intent == "tickets":
        tickets = build_today(db, current_user)["tickets"]
        if not tickets:
            out["reply"] = "No tienes tickets abiertos ahora mismo."
        elif len(tickets) == 1:
            out["reply"] = f"Tienes un ticket abierto, de {tickets[0]['client_name']}: {tickets[0]['problem']}. Lo abro."
            out["navigate_to"] = f"/proyectos/{tickets[0]['project_id']}?tab=tickets"
        else:
            names = ", ".join(t["client_name"] for t in tickets[:3])
            out["reply"] = f"Tienes {len(tickets)} tickets abiertos: {names}. Tócalos en la lista de abajo para abrirlos."
    elif intent == "none":
        out["reply"] = "De acuerdo. Aquí estoy cuando me necesites."
    return out


UNHEARD_REPLY = "No te escuché bien. ¿Me lo repites?"


@router.post("/listen", response_model=TalkOut)
async def listen(
    audio: UploadFile = File(...),
    survey_types: str = Form("[]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    """Un turno HABLADO de la conversación: recibe el audio grabado en el teléfono, lo transcribe
    con Whisper local y responde igual que `/talk`. Se hace en el servidor porque el dictado del
    navegador falla seguido en iPhone; grabar y transcribir aquí funciona igual en todos."""
    base_type = (audio.content_type or "").split(";")[0].strip().lower()
    if not base_type.startswith("audio/") and base_type not in ("video/mp4", "video/webm", "application/octet-stream"):
        raise HTTPException(status_code=400, detail=f"Tipo de archivo no permitido: {audio.content_type}")
    try:
        types = [str(t) for t in json.loads(survey_types)][:30]
    except (ValueError, TypeError):
        types = []

    contents = await audio.read()
    enforce_upload_size(contents)
    suffix = Path(audio.filename or "").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(contents)
        tmp_path = Path(tmp.name)
    try:
        heard = transcribe_audio(tmp_path, initial_prompt=CONVERSATION_PROMPT)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not heard.strip():
        return {"intent": "unheard", "reply": UNHEARD_REPLY, "heard": ""}
    return {**_respond(db, current_user, heard, types), "heard": heard}
