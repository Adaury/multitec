"""Bloqueo temporal tras intentos de acceso fallidos.

Dos contadores por cada intento fallido:

  * **cuenta + IP** (el estricto): tras 5 fallos seguidos desde la misma IP contra la misma cuenta, esa IP espera
    1, 2, 5 y luego 15 minutos antes de poder probar otra clave en esa cuenta.
  * **solo la cuenta** (el amplio): tras 25 fallos desde cualquier IP (alguien probando claves desde muchas
    direcciones), la cuenta entera espera igual.

Antes era solo por cuenta, y eso permitía a cualquiera que supiera un correo (p. ej. admin@…) dejar a su dueño fuera
del sistema con 5 intentos cada 15 minutos. Con el contador por IP, el atacante se bloquea a sí mismo y el dueño
entra desde su propia conexión; el contador amplio sigue frenando la adivinación repartida entre muchas IPs.

Se cuenta igual exista o no el correo, para que la respuesta no diga qué cuentas existen. Vive en memoria del proceso
(una sola instancia del servidor): un reinicio lo borra, que es aceptable para frenar adivinación de claves.
"""

import threading
import time

MAX_FREE_ATTEMPTS = 5
MAX_ACCOUNT_ATTEMPTS = 25
# Segundos de espera tras el primer fallo de más, el siguiente... (el último se repite).
_WAITS = (60, 120, 300, 900)
_FORGET_AFTER = 3600  # sin actividad durante una hora, se olvida el historial
_MAX_TRACKED = 20_000

_lock = threading.Lock()
_state: dict[str, tuple[int, float, float]] = {}  # clave -> (fallos, bloqueado_hasta, último_fallo)


def _keys(identifier: str, ip: str | None) -> list[tuple[str, int]]:
    account = identifier.strip().lower()
    return [(f"{account}|{ip or '-'}", MAX_FREE_ATTEMPTS), (account, MAX_ACCOUNT_ATTEMPTS)]


def seconds_locked(identifier: str, ip: str | None = None) -> int:
    """Segundos que faltan para que se acepte otro intento de esta cuenta desde esta IP (0 si se puede)."""
    now = time.monotonic()
    wait = 0.0
    with _lock:
        for key, _limit in _keys(identifier, ip):
            entry = _state.get(key)
            if entry is not None:
                wait = max(wait, entry[1] - now)
    return int(wait) + 1 if wait > 0 else 0


def register_failure(identifier: str, ip: str | None = None) -> None:
    now = time.monotonic()
    with _lock:
        if len(_state) >= _MAX_TRACKED:
            for stale in [k for k, (_, _, last) in _state.items() if now - last > _FORGET_AFTER]:
                del _state[stale]
        for key, limit in _keys(identifier, ip):
            failures, _, last = _state.get(key, (0, 0.0, now))
            if now - last > _FORGET_AFTER:
                failures = 0
            failures += 1
            locked_until = 0.0
            if failures >= limit:
                locked_until = now + _WAITS[min(failures - limit, len(_WAITS) - 1)]
            _state[key] = (failures, locked_until, now)


def register_success(identifier: str, ip: str | None = None) -> None:
    with _lock:
        for key, _limit in _keys(identifier, ip):
            _state.pop(key, None)


def reset() -> None:
    """Para las pruebas."""
    with _lock:
        _state.clear()
