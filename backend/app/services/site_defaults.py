"""Planes y testimonios de muestra con los que arranca la página pública. Los planes son una PROPUESTA editable desde
el panel (precios en US$, tomando de referencia RD$2,500/mes y RD$10,000 de instalación). Los testimonios son
borradores de ejemplo, sin publicar: hay que reemplazarlos por opiniones reales antes de mostrarlos."""

from sqlalchemy.orm import Session

from app.models.site import PlatformPlan, Testimonial

DEFAULT_PLANS = [
    {
        "name": "Básico",
        "description": "Para empezar a ordenar tu empresa",
        "monthly_price": 40,
        "setup_price": 160,
        "max_users": 4,
        "highlighted": False,
        "sort": 1,
        "features": [
            "1 administrador y 3 técnicos",
            "Clientes y proyectos ilimitados",
            "Levantamientos con fotos y voz",
            "Cotizaciones en PDF y por WhatsApp",
            "Catálogo base de cámaras, alarmas y cercos",
            "Soporte por WhatsApp",
        ],
    },
    {
        "name": "Profesional",
        "description": "El más elegido por empresas en crecimiento",
        "monthly_price": 60,
        "setup_price": 160,
        "max_users": 10,
        "highlighted": True,
        "sort": 2,
        "features": [
            "Hasta 10 usuarios",
            "Todo lo del plan Básico",
            "Cotización con inteligencia artificial",
            "Facturas con NCF y reportes 606 / 607",
            "Portal para que tu cliente vea y apruebe",
            "Inventario, compras y tickets",
        ],
    },
    {
        "name": "Empresarial",
        "description": "Para equipos grandes",
        "monthly_price": 95,
        "setup_price": 250,
        "max_users": None,
        "highlighted": False,
        "sort": 3,
        "features": [
            "Usuarios ilimitados",
            "Todo lo del plan Profesional",
            "Capacitación de todo tu equipo",
            "Soporte prioritario",
            "Importación de tu catálogo y clientes",
        ],
    },
]

EXAMPLE_TESTIMONIALS = [
    {
        "author": "Nombre del cliente",
        "role": "Dueño",
        "company": "Empresa de ejemplo SRL",
        "quote": "EJEMPLO — reemplázalo por la opinión real de un cliente. Antes hacíamos las cotizaciones a mano y "
        "tardábamos un día; ahora salen en minutos desde el celular.",
        "sort": 1,
    },
    {
        "author": "Nombre del cliente",
        "role": "Técnico",
        "company": "Empresa de ejemplo",
        "quote": "EJEMPLO — reemplázalo por la opinión real de un cliente. Hago el levantamiento hablando y la "
        "oficina ya tiene todo para cotizar.",
        "sort": 2,
    },
    {
        "author": "Nombre del cliente",
        "role": "Administradora",
        "company": "Empresa de ejemplo",
        "quote": "EJEMPLO — reemplázalo por la opinión real de un cliente. Sé qué técnico está en cada visita y qué "
        "falta por cobrar.",
        "sort": 3,
    },
]


def ensure_site_defaults(db: Session) -> None:
    """Crea los planes y los borradores de testimonios la primera vez (si ya hay, no toca nada)."""
    if db.query(PlatformPlan.id).first() is None:
        for plan in DEFAULT_PLANS:
            db.add(PlatformPlan(**plan))
    if db.query(Testimonial.id).first() is None:
        for t in EXAMPLE_TESTIMONIALS:
            db.add(Testimonial(**t, rating=5, published=False, is_example=True))
    db.commit()
