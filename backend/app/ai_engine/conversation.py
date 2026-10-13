"""Conversación del Inicio: el asistente pregunta "¿qué toca hoy?" y entiende lo que el técnico
contesta hablando ("un levantamiento de cámaras para Juan Pérez", "continuar con la ferretería",
"qué tengo hoy").

Primero reglas (instantáneas y predecibles: una conversación no puede esperar 15 s por turno en
esta máquina sin GPU). La IA local solo entra cuando las reglas no reconocen la frase, y con una
respuesta mínima (la intención y el cliente). Si Ollama no responde, se pide repetir con ejemplos:
nunca se inventa una acción."""

import json
import logging
import re

from app.ai_engine.intake import TYPE_SYNONYMS, _fold, extract_phone, match_survey_type
from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings

logger = logging.getLogger("multitec.ai")

INTENTS = ("new_survey", "open_project", "agenda", "quotes", "tickets", "none")

INTENT_SCHEMA = {
    "type": "object",
    "properties": {"intent": {"type": "string", "enum": list(INTENTS)}, "client": {"type": "string"}},
    "required": ["intent", "client"],
}

_TICKET_WORDS = ("ticket", "tickets", "soporte", "averia", "averias", "reparar", "reparacion", "garantia", "falla")
_CONTINUE_WORDS = ("continuar", "continuo", "seguir", "sigo", "retomar", "retomo", "terminar", "termino", "abrir", "abre")
_NEW_WORDS = (
    "levantamiento", "levantamientos", "levantar", "cotizar", "cotizarle", "instalar", "instalacion",
    "instalarle", "presupuesto", "nuevo", "nueva", "medir", "medicion", "visitar", "ir donde", "pasar donde",
    "ir a casa", "pasar por",
)
_QUOTE_WORDS = ("cotizaciones", "pendientes de aprobar", "esperando respuesta")
_AGENDA_WORDS = ("agenda", "calendario", "visitas", "visita", "pendiente", "pendientes")
_AGENDA_PHRASES = ("que tengo", "que hay", "que toca", "que me toca", "como esta el dia", "para hoy")
_NONE_PHRASES = ("nada", "ninguna", "solo viendo", "solo mirando", "despues", "luego", "ahora no")

# Lo que suele venir justo antes del nombre del cliente.
_TITLES = r"(?:se[nñ]or|se[nñ]ora|don|do[nñ]a|doctor|doctora|ingeniero|ingeniera|licenciado|licenciada)"
_NAME_MARKERS = re.compile(
    r"\b(?:para\s+(?:el|la)\s+client[ea]|(?:el|la)\s+client[ea](?:\s+se\s+llama|\s+es)?|se\s+llama|"
    r"casa\s+de|donde|para|con|"
    # "a" solo cuenta si le sigue un tratamiento o un nombre propio ("visitar a don Ramón",
    # "visitar a Ramón"): si no, "voy a medir" daría el cliente "Medir".
    rf"a(?=\s+(?:(?:el|la)\s+)?{_TITLES}\b)|a(?=\s+(?-i:[A-ZÁÉÍÓÚÑ])))\s+"
    # Artículo y tratamiento no son parte del nombre: "para la doctora Jiménez" -> "Jiménez".
    rf"(?:(?:el|la|del)\s+)?(?:{_TITLES}\s+)?",
    re.IGNORECASE,
)
# Palabras que cortan el nombre ("para Juan Pérez de cámaras en Santiago").
_NAME_STOP = {
    "de", "del", "en", "y", "que", "con", "para", "por", "un", "una", "el", "la", "los", "las", "hoy",
    "manana", "tipo", "su", "al", "a", "quiere", "necesita", "tiene",
}
_TYPE_WORDS = {s for synonyms in TYPE_SYNONYMS.values() for s in synonyms} | {
    "camara", "camaras", "alarma", "alarmas", "acceso", "cerco", "red", "redes", "seguridad", "sistema",
    "levantamiento", "cotizacion", "instalacion",
}


def _has_word(folded: str, words: tuple[str, ...]) -> bool:
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    return any((w in tokens) if " " not in w else (w in folded) for w in words)


def extract_client_name(text: str) -> str:
    """El nombre del cliente dentro de una frase libre: lo que sigue al último marcador ("para",
    "el cliente", "se llama"...) hasta una palabra de corte. "" si no hay nada que parezca nombre."""
    best = ""
    for match in _NAME_MARKERS.finditer(text):
        words: list[str] = []
        for raw in text[match.end():].split():
            word = raw.strip(",.;:¿?¡!\"'")
            folded = _fold(word)
            if not word or folded in _NAME_STOP or folded in _TYPE_WORDS or any(ch.isdigit() for ch in word):
                break
            words.append(word)
            if len(words) == 4:
                break
        candidate = " ".join(words)
        if len(candidate) >= 3:
            best = candidate  # gana el último marcador: "levantamiento para cámaras para Juan Pérez"
    return best.title() if best == best.lower() else best


def match_project(text: str, projects: list[dict]) -> dict | None:
    """El proyecto abierto cuyo cliente se nombra en la frase. Exige que coincidan todas las
    palabras significativas del nombre del cliente, o al menos dos, para no abrir uno al azar."""
    tokens = set(re.findall(r"[a-z0-9]+", _fold(text)))
    best: tuple[int, dict] | None = None
    for project in projects:
        name_tokens = [t for t in re.findall(r"[a-z0-9]+", _fold(project["client_name"])) if len(t) >= 3]
        if not name_tokens:
            continue
        hits = sum(1 for t in name_tokens if t in tokens)
        if hits == len(name_tokens) or hits >= 2:
            if best is None or hits > best[0]:
                best = (hits, project)
    return best[1] if best else None


def classify_by_rules(text: str) -> str | None:
    """La intención según palabras clave, o None si la frase no encaja con nada conocido."""
    folded = _fold(text)
    if not folded.strip():
        return None
    if _has_word(folded, _TICKET_WORDS):
        return "tickets"
    if _has_word(folded, _CONTINUE_WORDS):
        return "open_project"
    if any(p in folded for p in _QUOTE_WORDS):
        return "quotes"
    if _has_word(folded, _NEW_WORDS):
        return "new_survey"
    if _has_word(folded, _AGENDA_WORDS) or any(p in folded for p in _AGENDA_PHRASES):
        return "agenda"
    # Decir solo el tipo de trabajo ("unas cámaras para...") también es pedir un levantamiento.
    tokens = set(re.findall(r"[a-z0-9]+", folded))
    if tokens & {s for synonyms in TYPE_SYNONYMS.values() for s in synonyms}:
        return "new_survey"
    if any(p in folded for p in _NONE_PHRASES):
        return "none"
    return None


def classify_with_model(text: str) -> tuple[str | None, str]:
    """Último recurso: la IA local dice la intención y, si lo hay, el cliente. (None, "") si falla."""
    settings = get_settings()
    prompt = (
        "Un técnico de seguridad electrónica le dice a su asistente qué quiere hacer hoy. Clasifica "
        "la frase en UNA intención:\n"
        "- new_survey: hacer un levantamiento o una cotización nueva para un cliente.\n"
        "- open_project: continuar o abrir un proyecto que ya existe.\n"
        "- agenda: saber qué tiene pendiente o agendado hoy.\n"
        "- quotes: revisar cotizaciones pendientes.\n"
        "- tickets: atender un ticket de soporte o una avería.\n"
        "- none: no quiere hacer nada ahora o no es ninguna de las anteriores.\n"
        'En "client" copia el nombre del cliente si lo dijo, o "" si no.\n\n'
        f"Frase: {text}"
    )

    def run():
        response = get_client().chat(
            model=settings.ai_model,
            format=INTENT_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            # Respuesta mínima: en CPU cada token cuesta ~0.4 s.
            options={**OLLAMA_OPTIONS, "temperature": 0, "num_predict": 40},
        )
        return json.loads(response.message.content)

    try:
        data = _call(run)
    except Exception:
        logger.warning("Conversación: la IA no respondió; se pide repetir")
        return None, ""
    intent = data.get("intent")
    return (intent if intent in INTENTS else None), str(data.get("client") or "").strip()


def understand(text: str, survey_types: list[str], projects: list[dict], use_model: bool = True) -> dict:
    """Qué quiere hacer el técnico. Devuelve la intención y lo que se pudo sacar de la frase
    (cliente, teléfono, tipo, proyecto). `projects` son sus proyectos abiertos, para "continuar"."""
    result = {
        "intent": None,
        "client_name": "",
        "phone": extract_phone(text),
        "survey_type": match_survey_type(text, survey_types),
        "project": None,
        "ai_used": False,
    }
    intent = classify_by_rules(text)
    project = match_project(text, projects)

    if intent is None and project is not None:
        intent = "open_project"  # solo nombró a un cliente con proyecto abierto
    if intent is None and use_model and text.strip():
        intent, ai_client = classify_with_model(text)
        if intent == "none":
            # Que la IA diga "nada" de una frase que las reglas no reconocieron es no haber
            # entendido: se pide repetir en vez de despedirse.
            intent = None
        result["ai_used"] = intent is not None
        if ai_client and intent == "new_survey":
            result["client_name"] = ai_client

    if intent == "open_project":
        result["project"] = project
    elif intent == "new_survey" and not result["client_name"]:
        result["client_name"] = extract_client_name(text)

    result["intent"] = intent
    return result
