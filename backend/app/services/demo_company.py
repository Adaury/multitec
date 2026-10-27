"""Empresa de demostración: para que los técnicos prueben la app un tiempo sin tocar datos de nadie.

Se crea desde el panel de plataforma con un administrador y varios técnicos de prueba, y con unos clientes y proyectos de
ejemplo ya repartidos entre los técnicos. Vence sola (periodo de prueba) y no se puede confundir con una empresa real:
tiene `is_demo` y sus datos llevan «(ejemplo)»."""

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.engineering import Engineering
from app.models.project import Project
from app.models.survey import Survey
from app.models.user import User
from app.services.code_generator import next_code
from app.services.execution import ensure_stages

# example.com está reservado por la IANA para ejemplos: nunca recibe correo de verdad.
DEMO_EMAIL_DOMAIN = "example.com"

_CLIENTS = [
    ("Residencial Los Arcos (ejemplo)", "Av. Principal #120, Santo Domingo", "Instalar 8 cámaras IP con grabador y acceso remoto."),
    ("Colmado Don Pepe (ejemplo)", "Calle Duarte #45, Santiago", "Alarma con sensores de movimiento y sirena; 4 cámaras interiores."),
    ("Taller Mecánico Ramírez (ejemplo)", "Carretera Sánchez km 9", "Cerco eléctrico y control de acceso para el portón."),
]


def demo_email(kind: str, number: int, slug: str) -> str:
    return f"{kind}{number}.{slug}@{DEMO_EMAIL_DOMAIN}"


def seed_demo_content(db: Session, admin_id: int, technician_ids: list[int]) -> None:
    """Clientes y proyectos de ejemplo. `db` es una sesión de la empresa demo."""
    for index, (name, address, description) in enumerate(_CLIENTS):
        client = Client(name=name, address=address, created_by=admin_id)
        db.add(client)
        db.flush()
        project = Project(
            code=next_code(db, "PRY"),
            client_id=client.id,
            responsible_id=technician_ids[index % len(technician_ids)] if technician_ids else None,
            description=description,
            address=address,
            created_by=admin_id,
        )
        db.add(project)
        db.flush()
        db.add(Survey(project_id=project.id, created_by=admin_id))
        db.add(Engineering(project_id=project.id, created_by=admin_id))
        ensure_stages(db, project)
    db.commit()


def build_users(company_id: int, slug: str, technicians: int, created_by: int, hash_password, new_password) -> list[tuple[User, str]]:
    """Admin de la demo + técnicos, cada uno con su clave temporal. Devuelve (usuario, clave) para mostrarla una vez."""
    specs = [("Administrador Demo", demo_email("admin", 1, slug), "admin")]
    specs += [(f"Técnico Demo {n}", demo_email("tecnico", n, slug), "tecnico") for n in range(1, technicians + 1)]
    out = []
    for name, email, role in specs:
        password = new_password()
        out.append(
            (
                User(
                    company_id=company_id,
                    name=name,
                    email=email,
                    hashed_password=hash_password(password),
                    role=role,
                    must_change_password=True,
                    created_by=created_by,
                ),
                password,
            )
        )
    return out
