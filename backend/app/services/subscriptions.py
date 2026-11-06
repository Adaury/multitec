"""Suscripciones de las empresas a la plataforma: prueba, instalación, mensualidad y pagos.

Modelo de cobro (configurable en .env, ver core/config.py): la empresa se registra sola y tiene PLATFORM_TRIAL_DAYS de
prueba; luego paga una vez la instalación y explicación (PLATFORM_SETUP_FEE) y cada mes el soporte y uso
(PLATFORM_MONTHLY_FEE). Los pagos los registra la plataforma a mano: cada mes pagado corre «pagado hasta» un mes.
"""

import calendar
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.company import Company, CompanyPayment
from app.models.site import PlatformPlan

PAYMENT_KINDS = ("instalacion", "mensualidad")
PAYMENT_METHODS = ("transferencia", "deposito", "efectivo", "tarjeta", "otro")


def add_months(value: datetime, months: int) -> datetime:
    """Mismo día del mes `months` meses después (el 31 de enero + 1 = 28/29 de febrero)."""
    month0 = value.month - 1 + months
    year, month = value.year + month0 // 12, month0 % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def contact_phones() -> list[str]:
    return [p.strip() for p in get_settings().platform_contact_phone.split(",") if p.strip()]


def plan_of(company: Company) -> PlatformPlan | None:
    if company.plan_id is None:
        return None
    from sqlalchemy.orm import object_session

    db = object_session(company)
    return db.get(PlatformPlan, company.plan_id) if db is not None else None


def fees(company: Company) -> tuple[float, float]:
    """Instalación y mensualidad de la empresa: su tarifa propia, si no la de su plan, si no la general."""
    settings = get_settings()
    plan = plan_of(company)
    setup = (
        float(company.setup_fee) if company.setup_fee is not None
        else float(plan.setup_price) if plan is not None else float(settings.platform_setup_fee)
    )
    monthly = (
        float(company.monthly_fee) if company.monthly_fee is not None
        else float(plan.monthly_price) if plan is not None else float(settings.platform_monthly_fee)
    )
    return setup, monthly


def payment_info(db: Session) -> str:
    """Cómo pagarle a la plataforma: lo del .env o, si está vacío, las cuentas de «Mi empresa» de la empresa 1 (las
    mismas que salen en las cotizaciones)."""
    from app.db.tenant import tenant_bypass
    from app.models.company_profile import CompanyProfile

    configured = get_settings().platform_payment_info.replace("\\n", "\n")
    if configured.strip():
        return configured
    with tenant_bypass(db):
        profile = db.query(CompanyProfile).filter(CompanyProfile.company_id == 1).first()
    return (profile.bank_info or "") if profile is not None else ""


def new_trial_end() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=get_settings().platform_trial_days)


def register_payment(
    db: Session,
    company: Company,
    *,
    kind: str,
    amount: float,
    months: int,
    method: str,
    paid_at: date,
    reference: str | None,
    notes: str | None,
    user_id: int | None,
) -> CompanyPayment:
    """Anota el pago. Si cubre meses, «pagado hasta» avanza desde hoy o desde lo ya pagado (lo que sea más tarde), y la
    prueba se termina: la empresa pasa a ser de pago. No hace commit."""
    now = datetime.now(timezone.utc)
    if kind == "instalacion" and company.setup_paid_at is None:
        company.setup_paid_at = datetime.combine(paid_at, datetime.min.time(), tzinfo=timezone.utc)
    if months > 0:
        base = _utc(company.paid_until) if company.paid_until is not None else now
        if base < now:
            base = now
        company.paid_until = add_months(base, months)
        company.trial_ends_at = None
    payment = CompanyPayment(
        company_id=company.id,
        kind=kind,
        amount=amount,
        months=months,
        method=method,
        reference=(reference or None),
        notes=(notes or None),
        paid_at=paid_at,
        paid_until_after=company.paid_until,
        recorded_by=user_id,
    )
    db.add(payment)
    return payment


def payments_of(db: Session, company_id: int) -> list[CompanyPayment]:
    return (
        db.query(CompanyPayment)
        .filter(CompanyPayment.company_id == company_id)
        .order_by(CompanyPayment.paid_at.desc(), CompanyPayment.id.desc())
        .all()
    )


def summary(db: Session) -> dict:
    """Números del panel: empresas por estado, solicitudes nuevas, las que vencen pronto, cobrado este mes y lo que
    se espera cobrar por mes."""
    companies = db.query(Company).filter(Company.is_demo.is_(False)).all()
    by_state: dict[str, int] = {}
    for c in companies:
        by_state[c.state] = by_state.get(c.state, 0) + 1
    soon = sorted(
        (c for c in companies if c.is_active and c.days_left is not None and c.days_left <= 7),
        key=lambda c: c.days_left,
    )
    today = date.today()
    month_start = today.replace(day=1)
    collected = db.query(func.coalesce(func.sum(CompanyPayment.amount), 0)).filter(CompanyPayment.paid_at >= month_start).scalar()
    paying = [c for c in companies if c.paid_until is not None and c.state in ("activa", "atrasada")]
    monthly = sum(fees(c)[1] for c in paying)
    return {
        "by_state": by_state,
        "new_requests": [
            {"id": c.id, "name": c.name, "created_at": c.created_at, "contact_name": c.contact_name,
             "contact_email": c.contact_email, "contact_phone": c.contact_phone, "days_left": c.days_left}
            for c in sorted(companies, key=lambda c: c.created_at, reverse=True)
            if c.source == "registro" and c.reviewed_at is None
        ],
        "expiring": [{"id": c.id, "name": c.name, "state": c.state, "days_left": c.days_left} for c in soon],
        "currency": get_settings().platform_currency,
        "collected_this_month": float(collected or Decimal(0)),
        "expected_monthly": monthly,
        "paying_companies": len(paying),
    }


def notice_for(company: Company) -> str | None:
    """Aviso para el administrador de la empresa cuando falta poco o ya está en días de gracia (None = nada que avisar)."""
    days = company.days_left
    state = company.state
    if state == "atrasada":
        return "Tu mensualidad venció. Realiza el pago para no perder el acceso en los próximos días."
    if state == "prueba" and days is not None and days <= 7:
        return f"Tu prueba gratis termina en {max(days, 0)} día(s). Coordina la instalación con Multitec para seguir usando el sistema."
    if state == "activa" and company.paid_until is not None and days is not None and days <= 5:
        return f"Tu mensualidad vence en {max(days, 0)} día(s)."
    return None
