import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Iterable

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
import jwt
from jwt import PyJWTError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.timeutil import as_utc
from app.db.session import get_db
from app.db.tenant import tenant_bypass
from app.models.company import COMPANY_SUSPENDED, Company  # noqa: F401  (COMPANY_SUSPENDED se re-exporta)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services.access import enforce_assignment_scope

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # bcrypt.checkpw truena (ValueError) con passwords de más de 72 bytes. El login no
    # tiene el límite de longitud que sí valida UserCreate/UserUpdate (OAuth2PasswordRequestForm
    # no lo restringe), así que sin este guard un intento de login con un password larguísimo
    # tumba el endpoint con un 500 en vez de simplemente no coincidir.
    if len(plain_password.encode("utf-8")) > 72:
        return False
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


# Hash de un password inventado, fijo por proceso — se usa como stand-in en login cuando
# el email no existe, para que verify_password() corra siempre y el tiempo de respuesta no
# delate si un email está o no registrado (ver app/api/routers/auth.py::login).
DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-normalization")


def create_access_token(subject: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_support_token(user_id: int, company_id: int, allow_changes: bool, minutes: int) -> tuple[str, datetime]:
    """Token de soporte: el administrador de la plataforma entra a una empresa como su administrador por `minutes`.
    No tiene refresh: al vencer, se vuelve al panel. `support_write` falso = solo lectura (ver get_current_user)."""
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=minutes)
    payload = {"sub": str(user_id), "exp": expire, "support_company": company_id, "support_write": bool(allow_changes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm), expire


SUPPORT_READ_ONLY = "Modo soporte de solo lectura: vuelve a entrar con «Permitir cambios» para modificar datos."
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def _support_user(request: Request, db: Session, user: User, payload: dict) -> User:
    """Convierte al administrador de la plataforma en «administrador de la empresa X» solo para esta petición.

    El objeto del usuario se separa de la sesión (expunge) antes de cambiarle la empresa y el rol, así nada de eso se
    guarda nunca en su cuenta real. Las escrituras se rechazan en solo lectura y, con cambios permitidos, cada una queda
    anotada en la auditoría de la empresa atendida."""
    from app.services.audit import audit

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="La sesión de soporte terminó", headers={"WWW-Authenticate": "Bearer"}
    )
    if not user.is_platform_admin:
        raise credentials_exception
    try:
        company_id = int(payload["support_company"])
    except (KeyError, TypeError, ValueError):
        raise credentials_exception from None
    with tenant_bypass(db):
        target = db.get(Company, company_id)
    if target is None:
        raise credentials_exception
    allow_changes = bool(payload.get("support_write"))
    is_write = request.method not in _SAFE_METHODS and request.url.path != "/api/auth/logout"
    if is_write and (not allow_changes or request.url.path.startswith(("/api/auth/", "/api/platform/"))):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=SUPPORT_READ_ONLY)
    # Se separa de la sesión ANTES de cualquier commit (el de la auditoría vencería sus datos y ya no se podrían leer).
    db.expunge(user)
    # La sesión pasa a ser de la empresa atendida antes de escribir nada (también el registro de auditoría).
    db.info["company_id"] = target.id
    db.info["support_user_id"] = user.id
    if is_write:
        audit(
            db,
            "support_change",
            user=user,
            company_id=target.id,
            entity="support",
            detail={"metodo": request.method, "ruta": request.url.path},
            request=request,
            commit=True,
        )
    user.company_id = target.id
    user.company = target
    user.role = "admin"
    user.must_change_password = False
    user.support_mode = True
    user.support_write = allow_changes
    user.support_expires_at = datetime.fromtimestamp(int(payload["exp"]), tz=timezone.utc)
    db.info["company_id"] = target.id
    return user


def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_refresh_token(db: Session, user_id: int, request: Request | None = None) -> str:
    """Genera un refresh token de alta entropía; solo su hash SHA-256 se guarda en la
    base de datos, así un dump de la base no permite reusar tokens directamente.
    Con `request` se anotan el dispositivo y la IP para mostrar "sesiones activas"."""
    settings = get_settings()
    raw_token = secrets.token_urlsafe(48)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.refresh_token_expire_days)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash_refresh_token(raw_token),
            expires_at=expires_at,
            user_agent=(request.headers.get("user-agent") or "")[:255] or None if request else None,
            ip=request.client.host if request is not None and request.client else None,
            last_used_at=now,
        )
    )
    db.commit()
    return raw_token


def get_valid_refresh_token(db: Session, raw_token: str) -> RefreshToken | None:
    token_hash = _hash_refresh_token(raw_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).one_or_none()
    if row is None:
        return None

    if row.revoked:
        # Un token ya revocado (rotado en un /refresh anterior) que vuelve a usarse es la
        # señal clásica de que fue robado: alguien más lo usó primero. Se revoca toda la
        # sesión del usuario, no solo este token, para forzar un login limpio.
        db.query(RefreshToken).filter(
            RefreshToken.user_id == row.user_id, RefreshToken.revoked.is_(False)
        ).update({"revoked": True})
        db.commit()
        return None

    if as_utc(row.expires_at) < datetime.now(timezone.utc):
        return None
    return row


def revoke_refresh_token(db: Session, raw_token: str) -> None:
    token_hash = _hash_refresh_token(raw_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).one_or_none()
    if row is not None:
        row.revoked = True
        db.commit()


def revoke_all_refresh_tokens(db: Session, user_id: int) -> None:
    """Cierra todas las sesiones del usuario (cambio/reseteo de contraseña, desactivación).
    No hace commit: lo hace el llamador junto con el resto de su cambio, para que sea atómico."""
    db.query(RefreshToken).filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False)).update(
        {"revoked": True}
    )


def active_sessions(db: Session, user_id: int) -> list[RefreshToken]:
    """Sesiones abiertas de un usuario: refresh tokens no revocados y no vencidos, la más reciente primero."""
    now = datetime.now(timezone.utc)
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked.is_(False))
        .order_by(RefreshToken.created_at.desc())
        .all()
    )
    # La comparación de fechas se hace aquí: SQLite (pruebas) devuelve fechas sin zona.
    return [r for r in rows if as_utc(r.expires_at) > now]


# Con la contraseña temporal sin cambiar, el usuario solo puede verse a sí mismo y cambiarla.
PASSWORD_CHANGE_ALLOWED_PATHS = {"/api/auth/me", "/api/auth/change-password", "/api/auth/logout"}


def get_current_user(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    settings = get_settings()
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar la credencial",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # require: sin exp o sub el token no es válido (PyJWT no los exige por defecto).
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm], options={"require": ["exp", "sub"]}
        )
        user_id = int(payload["sub"])
    except (PyJWTError, ValueError):
        raise credentials_exception

    # Al autenticar todavía no se sabe de qué empresa es la sesión: el usuario se busca sin filtro y es él quien la fija.
    with tenant_bypass(db):
        user = db.get(User, user_id)
        company = db.get(Company, user.company_id) if user is not None else None
    if user is None or not user.is_active:
        raise credentials_exception
    if payload.get("support_company") is not None:
        # Soporte: entra aunque la empresa atendida esté suspendida o vencida (justo para ayudarla).
        return _support_user(request, db, user, payload)
    reason = company.access_block_reason if company is not None else COMPANY_SUSPENDED
    if reason:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=reason)
    if user.must_change_password and request.url.path not in PASSWORD_CHANGE_ALLOWED_PATHS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes cambiar tu contraseña temporal antes de continuar",
        )
    # Desde aquí, todo lo que la petición lea o escriba en esta sesión es de esta empresa y de ninguna otra.
    db.info["company_id"] = user.company_id
    return user




def require_platform_admin(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Solo el dueño de la plataforma. Su panel actúa sobre TODAS las empresas, así que el filtro por empresa se
    apaga para esta petición; cada escritura dentro de él debe indicar su empresa explícitamente."""
    if not current_user.is_platform_admin or getattr(current_user, "support_mode", False):
        # Con un token de soporte no se usa el panel: ese token solo vale dentro de la empresa atendida.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Solo el administrador de la plataforma")
    db.info["bypass_tenant"] = True
    return current_user


def require_role(*roles: Iterable[str]):
    allowed = set(roles)

    def dependency(
        request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
    ) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para realizar esta acción",
            )
        # Primero el rol (403), después la pertenencia: un técnico solo ve lo suyo en las rutas con
        # project_id, client_id, ticket_id... (ver services/access.py).
        enforce_assignment_scope(db, current_user, request.path_params)
        return current_user

    return dependency
