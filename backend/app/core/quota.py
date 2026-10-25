"""Cuota de uso de la IA por usuario.

La IA corre en la CPU de esta misma máquina (Ollama, Whisper): unas pocas peticiones largas en bucle, de un
técnico o de una sesión robada, dejan el servidor lento para todos. Esto limita cuántas llamadas puede hacer
cada usuario por minuto. Vive en memoria del proceso (una sola instancia); un reinicio la borra.
"""

import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.user import User

AI_CALLS_PER_MINUTE = 30
_WINDOW_SECONDS = 60

_lock = threading.Lock()
_calls: dict[int, deque[float]] = defaultdict(deque)


def ai_quota(current_user: User = Depends(get_current_user)) -> None:
    """Dependencia: deja pasar o responde 429 con cuánto esperar."""
    now = time.monotonic()
    with _lock:
        window = _calls[current_user.id]
        while window and now - window[0] > _WINDOW_SECONDS:
            window.popleft()
        if len(window) >= AI_CALLS_PER_MINUTE:
            wait = int(_WINDOW_SECONDS - (now - window[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Estás usando la IA muy seguido. Espera un momento e inténtalo de nuevo.",
                headers={"Retry-After": str(wait)},
            )
        window.append(now)


def reset() -> None:
    """Para las pruebas."""
    with _lock:
        _calls.clear()
