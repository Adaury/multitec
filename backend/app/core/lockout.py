"""Bloqueo temporal por cuenta tras intentos de acceso fallidos.

El límite por IP (slowapi, 10/min) no frena a quien rota de IP o va despacio contra una sola cuenta. Aquí se
cuenta por correo: tras 5 fallos seguidos la cuenta espera 1, 2, 5 y luego 15 minutos antes de aceptar otro
intento. Se cuenta igual exista o no el correo, para que la respuesta no diga qué cuentas existen.

Vive en memoria del proceso (una sola instancia del servidor): un reinicio lo borra, que es aceptable para
frenar adivinación de claves, y evita una tabla más. Si algún día hay varias instancias, pasarlo a la base.
"""

import threading
import time

MAX_FREE_ATTEMPTS = 5
# Segundos de espera tras el 5.º fallo, el 6.º, el 7.º... (el último se repite).
_WAITS = (60, 120, 300, 900)
_FORGET_AFTER = 3600  # sin actividad durante una hora, se olvida el historial de esa cuenta
_MAX_TRACKED = 10_000

_lock = threading.Lock()
_state: dict[str, tuple[int, float, float]] = {}  # clave -> (fallos, bloqueado_hasta, último_fallo)


def _key(identifier: str) -> str:
    return identifier.strip().lower()


def seconds_locked(identifier: str) -> int:
    """Segundos que faltan para que la cuenta acepte otro intento (0 si no está bloqueada)."""
    now = time.monotonic()
    with _lock:
        entry = _state.get(_key(identifier))
        if entry is None:
            return 0
        _, locked_until, _ = entry
        return max(0, int(locked_until - now) + (1 if locked_until > now else 0))


def register_failure(identifier: str) -> None:
    now = time.monotonic()
    key = _key(identifier)
    with _lock:
        if len(_state) >= _MAX_TRACKED:
            for stale in [k for k, (_, _, last) in _state.items() if now - last > _FORGET_AFTER]:
                del _state[stale]
        failures, _, last = _state.get(key, (0, 0.0, now))
        if now - last > _FORGET_AFTER:
            failures = 0
        failures += 1
        locked_until = 0.0
        if failures >= MAX_FREE_ATTEMPTS:
            wait = _WAITS[min(failures - MAX_FREE_ATTEMPTS, len(_WAITS) - 1)]
            locked_until = now + wait
        _state[key] = (failures, locked_until, now)


def register_success(identifier: str) -> None:
    with _lock:
        _state.pop(_key(identifier), None)


def reset() -> None:
    """Para las pruebas."""
    with _lock:
        _state.clear()
