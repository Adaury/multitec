from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.limiter import limiter
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_valid_refresh_token,
    revoke_refresh_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import CurrentUser, RefreshRequest, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    # Los emails se guardan normalizados a minúsculas (ver schemas/user.py) — se normaliza
    # igual acá para que el login no dependa de cómo el usuario tecleó las mayúsculas.
    user = db.query(User).filter(User.email == form_data.username.lower()).one_or_none()
    # verify_password corre siempre, incluso si el email no existe (contra el hash "dummy"),
    # para que el tiempo de respuesta no delate si un email está registrado.
    password_ok = verify_password(form_data.password, user.hashed_password if user else DUMMY_PASSWORD_HASH)
    if user is None or not password_ok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correo o contraseña incorrectos",
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario inactivo")

    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(db, user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=Token)
@limiter.limit("30/minute")
def refresh(request: Request, payload: RefreshRequest, db: Session = Depends(get_db)):
    row = get_valid_refresh_token(db, payload.refresh_token)
    if row is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token inválido o expirado")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario inactivo")

    # Rotación: este refresh token se revoca y se emite uno nuevo junto con el access
    # token — un refresh token es de un solo uso. Si alguien lo reusa después (porque lo
    # robó), get_valid_refresh_token lo detecta y revoca toda la sesión (ver security.py).
    row.revoked = True
    access_token = create_access_token(subject=str(user.id))
    refresh_token = create_refresh_token(db, user.id)
    return Token(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(payload: RefreshRequest, db: Session = Depends(get_db)):
    revoke_refresh_token(db, payload.refresh_token)


@router.get("/me", response_model=CurrentUser)
def me(current_user: User = Depends(get_current_user)):
    return current_user
