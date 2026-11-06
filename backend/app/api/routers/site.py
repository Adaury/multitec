"""Página pública de Multitec (/web) y su editor en el panel de plataforma: planes con precios y testimonios.

GET /api/site es público (sin sesión): planes activos, testimonios PUBLICADOS, teléfonos y días de prueba.
Las rutas /api/platform/site/* son solo del dueño de la plataforma y quedan en la auditoría.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import require_platform_admin
from app.db.session import get_db
from app.models.company import Company
from app.models.site import PlatformPlan, Testimonial
from app.models.user import User
from app.services import subscriptions
from app.services.audit import audit
from app.services.site_defaults import ensure_site_defaults

router = APIRouter(tags=["site"])


class PlanIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    description: str | None = Field(default=None, max_length=200)
    monthly_price: float = Field(ge=0, le=1_000_000)
    setup_price: float = Field(ge=0, le=1_000_000)
    max_users: int | None = Field(default=None, ge=1, le=10_000)
    features: list[str] = Field(default_factory=list, max_length=20)
    highlighted: bool = False
    active: bool = True
    sort: int = Field(default=0, ge=0, le=1000)

    @field_validator("features")
    @classmethod
    def _clean(cls, v: list[str]) -> list[str]:
        out = [f.strip()[:120] for f in v if f and f.strip()]
        return out


class PlanOut(PlanIn):
    id: int

    class Config:
        from_attributes = True


class TestimonialIn(BaseModel):
    author: str = Field(min_length=2, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    quote: str = Field(min_length=10, max_length=600)
    rating: int = Field(default=5, ge=1, le=5)
    published: bool = False
    sort: int = Field(default=0, ge=0, le=1000)


class TestimonialOut(TestimonialIn):
    id: int
    is_example: bool = False

    class Config:
        from_attributes = True


def _plans(db: Session, only_active: bool) -> list[PlatformPlan]:
    query = db.query(PlatformPlan)
    if only_active:
        query = query.filter(PlatformPlan.active.is_(True))
    return query.order_by(PlatformPlan.sort, PlatformPlan.id).all()


def _plan_out(p: PlatformPlan) -> PlanOut:
    return PlanOut(
        id=p.id, name=p.name, description=p.description, monthly_price=float(p.monthly_price),
        setup_price=float(p.setup_price), max_users=p.max_users, features=p.features or [], highlighted=p.highlighted,
        active=p.active, sort=p.sort,
    )


@router.get("/api/site")
def public_site(db: Session = Depends(get_db)):
    """Lo que muestra la página pública. No incluye datos de ninguna empresa ni testimonios sin publicar."""
    ensure_site_defaults(db)
    settings = get_settings()
    phones = subscriptions.contact_phones()
    return {
        "currency": settings.platform_currency,
        "trial_days": settings.platform_trial_days,
        "signup_enabled": settings.public_signup_enabled,
        "phones": phones,
        "plans": [_plan_out(p) for p in _plans(db, only_active=True)],
        "testimonials": [
            TestimonialOut.model_validate(t)
            for t in db.query(Testimonial)
            .filter(Testimonial.published.is_(True), Testimonial.is_example.is_(False))
            .order_by(Testimonial.sort, Testimonial.id)
        ],
    }


@router.get("/api/platform/site")
def platform_site(db: Session = Depends(get_db), _: User = Depends(require_platform_admin)):
    ensure_site_defaults(db)
    return {
        "currency": get_settings().platform_currency,
        "plans": [_plan_out(p) for p in _plans(db, only_active=False)],
        "testimonials": [
            TestimonialOut.model_validate(t) for t in db.query(Testimonial).order_by(Testimonial.sort, Testimonial.id)
        ],
    }


def _log(db: Session, request: Request, user: User, action: str, detail: dict) -> None:
    audit(db, action, user=user, company_id=user.company_id, entity="site", detail=detail, request=request)


@router.post("/api/platform/site/plans", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(request: Request, payload: PlanIn, db: Session = Depends(get_db), user: User = Depends(require_platform_admin)):
    plan = PlatformPlan(**payload.model_dump())
    db.add(plan)
    _log(db, request, user, "site_plan_created", {"plan": payload.name})
    db.commit()
    return _plan_out(plan)


@router.put("/api/platform/site/plans/{plan_id}", response_model=PlanOut)
def update_plan(
    request: Request, plan_id: int, payload: PlanIn, db: Session = Depends(get_db), user: User = Depends(require_platform_admin)
):
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    for key, value in payload.model_dump().items():
        setattr(plan, key, value)
    _log(db, request, user, "site_plan_edited", {"plan": plan.name, "mensual": payload.monthly_price})
    db.commit()
    return _plan_out(plan)


@router.delete("/api/platform/site/plans/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_plan(request: Request, plan_id: int, db: Session = Depends(get_db), user: User = Depends(require_platform_admin)):
    """Un plan que alguna empresa tiene contratado no se borra: se oculta (deja de ofrecerse)."""
    plan = db.get(PlatformPlan, plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    if db.query(Company.id).filter(Company.plan_id == plan_id).first() is not None:
        plan.active = False
    else:
        db.delete(plan)
    _log(db, request, user, "site_plan_deleted", {"plan": plan.name})
    db.commit()


@router.post("/api/platform/site/testimonials", response_model=TestimonialOut, status_code=status.HTTP_201_CREATED)
def create_testimonial(
    request: Request, payload: TestimonialIn, db: Session = Depends(get_db), user: User = Depends(require_platform_admin)
):
    t = Testimonial(**payload.model_dump(), is_example=False)
    db.add(t)
    _log(db, request, user, "site_testimonial_created", {"autor": payload.author, "publicado": payload.published})
    db.commit()
    return TestimonialOut.model_validate(t)


@router.put("/api/platform/site/testimonials/{testimonial_id}", response_model=TestimonialOut)
def update_testimonial(
    request: Request,
    testimonial_id: int,
    payload: TestimonialIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_platform_admin),
):
    t = db.get(Testimonial, testimonial_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Testimonio no encontrado")
    for key, value in payload.model_dump().items():
        setattr(t, key, value)
    # Al editarlo deja de ser «el ejemplo del sistema»: ahora es una opinión que el dueño escribió.
    t.is_example = False
    if t.published and "EJEMPLO" in t.quote.upper():
        raise HTTPException(status_code=400, detail="Reemplaza el texto de ejemplo por la opinión real antes de publicarlo")
    _log(db, request, user, "site_testimonial_edited", {"autor": t.author, "publicado": t.published})
    db.commit()
    return TestimonialOut.model_validate(t)


@router.delete("/api/platform/site/testimonials/{testimonial_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_testimonial(
    request: Request, testimonial_id: int, db: Session = Depends(get_db), user: User = Depends(require_platform_admin)
):
    t = db.get(Testimonial, testimonial_id)
    if t is None:
        raise HTTPException(status_code=404, detail="Testimonio no encontrado")
    db.delete(t)
    _log(db, request, user, "site_testimonial_deleted", {"autor": t.author})
    db.commit()
