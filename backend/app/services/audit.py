"""Bitácora de auditoría: quién hizo qué, cuándo y desde dónde.

Se llama desde los puntos que importan (acceso, usuarios, precios, facturas, NCF, datos de la empresa). Por
defecto NO hace commit: la fila entra en la misma transacción que el cambio que describe, así nunca queda un
registro de algo que no ocurrió ni un cambio sin registro. Para acciones sin otra escritura (un acceso
fallido) se pasa commit=True.
"""

import json

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.user import User

# Nunca se guardan claves ni tokens, aunque alguien los pase por descuido en `detail`.
_SECRET_KEYS = ("password", "token", "secret", "clave", "contrasena")
_MAX_DETAIL = 2000


def _clean(detail: dict | None) -> str | None:
    if not detail:
        return None
    safe = {k: v for k, v in detail.items() if not any(s in k.lower() for s in _SECRET_KEYS)}
    return json.dumps(safe, ensure_ascii=False, default=str)[:_MAX_DETAIL] or None


def client_ip(request: Request | None) -> str | None:
    if request is None or request.client is None:
        return None
    return request.client.host


def audit(
    db: Session,
    action: str,
    *,
    user: User | None = None,
    email: str | None = None,
    entity: str | None = None,
    entity_id: int | None = None,
    detail: dict | None = None,
    request: Request | None = None,
    commit: bool = False,
    company_id: int | None = None,
) -> None:
    """`company_id`: empresa a la que pertenece el registro. Por defecto la del usuario que actúa; si no hay (acceso
    fallido con un correo desconocido) queda vacío, y el servidor de sesión pone la de la sesión cuando la hay."""
    db.add(
        AuditLog(
            company_id=company_id if company_id is not None else (user.company_id if user else None),
            user_id=user.id if user else None,
            user_email=(user.email if user else email),
            action=action,
            entity=entity,
            entity_id=entity_id,
            detail=_clean(detail),
            ip=client_ip(request),
        )
    )
    if commit:
        db.commit()
