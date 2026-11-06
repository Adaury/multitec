"""Tope general de pedidos por IP para toda la API, antes de hacer cualquier trabajo.

slowapi (core/limiter.py) sigue poniendo los límites estrictos de login, portal, etc. Su `default_limits` no servía de
tope general: con la forma en que esta versión de FastAPI agrupa las rutas, solo se aplicaba a las rutas declaradas
directamente en la app (/api/health), no a las de cada router. Este middleware ASGI es el tope general: cuenta pedidos
por IP en ventanas de un minuto y responde 429 al instante (sin tocar la base de datos ni ocupar un hilo), así una sola
conexión que inunda el servidor se frena sola y los demás siguen trabajando.

La IP es la del visitante: uvicorn ya la tomó de X-Forwarded-For del proxy de confianza (--forwarded-allow-ips).
"""

import json
import threading
import time

LIMIT_PER_MINUTE = 600  # una oficina con varios usuarios detrás de la misma IP no llega a esto
# Pedidos hechos desde la propia máquina sin pasar por el proxy (pruebas automáticas, chequeos de estado). Desde internet
# nadie llega con esta IP: el proxy siempre agrega la del visitante y uvicorn usa esa.
_LOCAL = {"127.0.0.1", "::1"}
_MAX_TRACKED = 50_000

_lock = threading.Lock()
# Reloj del limitador (las pruebas lo fijan para no depender de en qué segundo del minuto corren).
_now = time.time
_window = 0
_counts: dict[str, int] = {}


def hit(ip: str) -> int:
    """Suma un pedido de `ip` en el minuto actual y devuelve cuántos lleva."""
    global _window, _counts
    window = int(_now() // 60)
    with _lock:
        if window != _window or len(_counts) > _MAX_TRACKED:
            _window = window
            _counts = {}
        count = _counts.get(ip, 0) + 1
        _counts[ip] = count
        return count


def reset() -> None:
    """Para las pruebas."""
    global _counts
    with _lock:
        _counts = {}


class PerIPRateLimit:
    def __init__(self, app, limit: int = LIMIT_PER_MINUTE, prefix: str = "/api/"):
        self.app = app
        self.limit = limit
        self.prefix = prefix

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not scope.get("path", "").startswith(self.prefix):
            return await self.app(scope, receive, send)
        client = scope.get("client")
        ip = client[0] if client else "-"
        if ip in _LOCAL or hit(ip) <= self.limit:
            return await self.app(scope, receive, send)
        retry = str(60 - int(_now()) % 60)
        body = json.dumps({"detail": "Demasiadas solicitudes. Espera un momento e inténtalo de nuevo."}).encode()
        await send({
            "type": "http.response.start",
            "status": 429,
            "headers": [(b"content-type", b"application/json"), (b"retry-after", retry.encode()),
                        (b"content-length", str(len(body)).encode())],
        })
        await send({"type": "http.response.body", "body": body})
