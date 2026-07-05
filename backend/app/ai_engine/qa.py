"""Asistente de preguntas y respuestas sobre expedientes de proyecto.

Transversal a los 7 motores (usa el expediente ya armado, no interpreta levantamientos ni
resuelve catálogo) — ver `app.services.embeddings` para la búsqueda semántica que le da
contexto cuando no se especifica un proyecto.
"""

from app.ai_engine.ollama_client import OLLAMA_OPTIONS, _call, get_client
from app.core.config import get_settings


def answer_question(project_context: str, question: str) -> str:
    settings = get_settings()
    client = get_client()

    def run():
        response = client.chat(
            model=settings.ai_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente que responde preguntas sobre proyectos de "
                        "seguridad electrónica usando únicamente la información de los "
                        "expedientes proporcionados (puede haber uno o varios, separados por "
                        "'---'). Si la respuesta no está en los expedientes, dilo claramente "
                        "en vez de inventar. Si hay varios proyectos, aclara a cuál te "
                        "refieres en la respuesta.\n\n"
                        f"Expediente(s):\n{project_context}"
                    ),
                },
                {"role": "user", "content": question},
            ],
            options=OLLAMA_OPTIONS,
        )
        return response.message.content or ""

    return _call(run)
