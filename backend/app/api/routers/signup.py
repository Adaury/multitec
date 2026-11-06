"""Registro público de empresas (página /registro) y «Mi suscripción» del administrador de cada empresa.

Una empresa se registra sola: se crea con su administrador (la clave la elige quien se registra), el catálogo de
clasificaciones y el catálogo base de artículos sin precio, y PLATFORM_TRIAL_DAYS de prueba. A la plataforma le llega
el aviso (campanita y correo) para coordinar la instalación y el cobro.
"""

import logging
import re
import unicodedata

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.security import hash_password, require_role
from app.db.seed import seed_new_company
from app.db.session import SessionLocal, get_db
from app.db.tenant import tenant_bypass
from app.models.company import Company
from app.models.company_profile import CompanyProfile
from app.models.notification import Notification
from app.models.site import PlatformPlan
from app.models.user import User
from app.schemas.platform import PaymentOut, SignupDone, SignupRequest, SubscriptionOut
from app.services import catalog_base, subscriptions
from app.services.audit import audit
from app.services.email import send_email

logger = logging.getLogger("multitec.signup")

router = APIRouter(tags=["signup"])


def _slug(db: Session, name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode("ascii").lower()
    base = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:50] or "empresa"
    slug, n = base, 2
    while db.query(Company.id).filter(Company.slug == slug).first() is not None:
        slug, n = f"{base}-{n}", n + 1
    return slug


@router.get("/api/signup/info")
def signup_info(db: Session = Depends(get_db)):
    """Lo que muestra la página de registro (sin datos de nadie): planes, moneda y días de prueba."""
    from app.api.routers.site import _plan_out, _plans
    from app.services.site_defaults import ensure_site_defaults

    ensure_site_defaults(db)
    s = get_settings()
    phones = subscriptions.contact_phones()
    return {
        "enabled": s.public_signup_enabled,
        "trial_days": s.platform_trial_days,
        "currency": s.platform_currency,
        "setup_fee": s.platform_setup_fee,
        "monthly_fee": s.platform_monthly_fee,
        "contact_phone": phones[0] if phones else "",
        "plans": [_plan_out(p) for p in _plans(db, only_active=True)],
    }


def _load_base_catalog(company_id: int, admin_id: int) -> None:
    from app.services.catalog_import import TEMPLATE_HEADERS, import_catalog_files
    from app.services.spreadsheets import build_csv_semicolon

    with SessionLocal(company_id=company_id) as db:
        seed_new_company(db)
        catalog_base.ensure_roots(db)
        data = build_csv_semicolon(TEMPLATE_HEADERS, catalog_base.all_rows())
        import_catalog_files(db, [("catalogo_base.csv", data)], admin_id, False, create_categories=True, only_create=True)


@router.post("/api/signup", response_model=SignupDone, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def signup(
    request: Request,
    payload: SignupRequest,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.public_signup_enabled:
        raise HTTPException(status_code=404, detail="El registro de empresas no está disponible")
    if payload.website:  # robot: se responde como si nada, pero no se crea nada
        raise HTTPException(status_code=400, detail="No se pudo completar el registro")
    if not payload.accept_terms:
        raise HTTPException(status_code=400, detail="Debes aceptar los términos del servicio")

    from app.services.site_defaults import ensure_site_defaults

    ensure_site_defaults(db)  # los planes existen aunque nadie haya abierto antes la página pública
    plan = db.get(PlatformPlan, payload.plan_id) if payload.plan_id else None
    if payload.plan_id and (plan is None or not plan.active):
        raise HTTPException(status_code=400, detail="Ese plan no está disponible")
    if plan is None:  # sin elegir: el plan destacado (o el primero)
        plan = (
            db.query(PlatformPlan).filter(PlatformPlan.active.is_(True))
            .order_by(PlatformPlan.highlighted.desc(), PlatformPlan.sort).first()
        )

    with tenant_bypass(db):
        if db.query(User.id).filter(User.email == payload.email).first() is not None:
            raise HTTPException(status_code=400, detail="Ya existe una cuenta con ese correo. Inicia sesión o usa otro correo.")
        company = Company(
            name=payload.company_name,
            slug=_slug(db, payload.company_name),
            source="registro",
            contact_name=payload.admin_name,
            contact_email=payload.email,
            contact_phone=payload.phone,
            trial_ends_at=subscriptions.new_trial_end(),
            plan_id=plan.id if plan is not None else None,
            max_users=plan.max_users if plan is not None else None,
        )
        db.add(company)
        db.flush()
        db.add(CompanyProfile(company_id=company.id, name=payload.company_name, phone=payload.phone, email=payload.email))
        admin = User(
            company_id=company.id,
            name=payload.admin_name,
            email=payload.email,
            hashed_password=hash_password(payload.password),
            role="admin",
            must_change_password=False,
        )
        db.add(admin)
        db.flush()
        audit(db, "company_signup", user=admin, company_id=company.id, entity="company", entity_id=company.id,
              detail={"empresa": company.name, "telefono": payload.phone}, request=request)
        # Aviso en la campanita de cada administrador de la plataforma.
        for platform_admin in db.query(User).filter(User.is_platform_admin.is_(True), User.is_active.is_(True)).all():
            db.add(Notification(
                company_id=platform_admin.company_id,
                user_id=platform_admin.id,
                title=f"Nueva empresa registrada: {company.name}",
                body=f"{payload.admin_name} · {payload.email} · {payload.phone}. Prueba de {settings.platform_trial_days} días.",
                link=f"/plataforma/{company.id}",
            ))
        db.commit()
        company_id, admin_id, trial_ends_at = company.id, admin.id, company.trial_ends_at

    try:
        _load_base_catalog(company_id, admin_id)
    except Exception:  # noqa: BLE001 — la empresa ya existe; el catálogo se puede cargar después desde Catálogo
        logger.exception("No se pudo cargar el catálogo base de la empresa %s", company_id)

    if settings.notification_email:
        background.add_task(
            send_email,
            settings.notification_email,
            f"Nueva empresa en Multitec: {payload.company_name}",
            f"Se registró {payload.company_name}.\n\nContacto: {payload.admin_name}\nCorreo: {payload.email}\n"
            f"Teléfono: {payload.phone}\n\nTiene {settings.platform_trial_days} días de prueba. "
            "Coordina la instalación desde el panel de plataforma.",
        )
    return SignupDone(company_name=payload.company_name, email=payload.email, trial_days=settings.platform_trial_days,
                      trial_ends_at=trial_ends_at)


@router.get("/api/subscription", response_model=SubscriptionOut)
def my_subscription(db: Session = Depends(get_db), current_user: User = Depends(require_role("admin"))):
    """«Mi suscripción»: estado, lo que se paga y el historial de pagos de la propia empresa."""
    settings = get_settings()
    with tenant_bypass(db):
        company = db.get(Company, current_user.company_id)
        payments = subscriptions.payments_of(db, company.id)
    setup_fee, monthly_fee = subscriptions.fees(company)
    return SubscriptionOut(
        company_name=company.name,
        state=company.state,
        trial_ends_at=company.trial_ends_at,
        paid_until=company.paid_until,
        days_left=company.days_left,
        setup_fee=setup_fee,
        monthly_fee=monthly_fee,
        setup_paid=company.setup_paid_at is not None,
        notice=subscriptions.notice_for(company),
        payment_info=subscriptions.payment_info(db),
        contact_phone=(subscriptions.contact_phones() or [""])[0],
        contact_phones=subscriptions.contact_phones(),
        plan_name=plan.name if (plan := subscriptions.plan_of(company)) is not None else None,
        currency=settings.platform_currency,
        payments=[PaymentOut.model_validate(p) for p in payments],
    )
