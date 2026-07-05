"""Motor 6 — Motor de generación documental (§ docs/ai-engine-architecture.md).

Por ahora solo cubre el borrador de ingeniería; el resto del pipeline (presupuesto,
cotización, prefactura) vive en `app.api.routers.ai` / `app.api.routers.budgets` /
`app.services.pre_invoice` y se reorganiza en una fase posterior.
"""

import json

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings

ENGINEERING_SCHEMA = {
    "type": "object",
    "properties": {
        "recommended_equipment": {"type": "string"},
        "distribution": {"type": "string"},
        "conduits": {"type": "string"},
        "wiring": {"type": "string"},
        "technical_design": {"type": "string"},
        "observations": {"type": "string"},
    },
    "required": [
        "recommended_equipment",
        "distribution",
        "conduits",
        "wiring",
        "technical_design",
        "observations",
    ],
}


def draft_engineering(project_context: str) -> dict:
    settings = get_settings()
    client = get_client()

    prompt = (
        "Eres un ingeniero de sistemas de seguridad electrónica. A partir del siguiente "
        "expediente de proyecto, redacta un borrador de ingeniería técnica en español. "
        "Sé concreto y práctico; si falta información para alguna sección, indícalo "
        "brevemente en vez de inventar.\n\n" + project_context
    )

    def run():
        response = client.chat(
            model=settings.ai_model,
            format=ENGINEERING_SCHEMA,
            messages=[{"role": "user", "content": prompt}],
            options=OLLAMA_OPTIONS,
        )
        return json.loads(response.message.content)

    return _call(run)
