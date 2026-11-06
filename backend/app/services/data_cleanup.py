"""Borrar datos de prueba: clientes (con todo lo que cuelga de ellos) y productos del catálogo.

Cómo decide qué borrar: recorre las llaves foráneas del modelo. Una fila que no puede existir sin su padre
(columna NOT NULL, p. ej. la cotización de un proyecto) se borra con él; una referencia opcional (columna que
admite NULL, p. ej. la factura de compra que se asoció a un proyecto o la partida que apuntaba a un producto) se
conserva y solo se suelta (queda en NULL). Así nunca queda una fila apuntando a algo que ya no existe y no se
pierde lo que tiene valor propio (las compras del 606, el texto de una partida).

Seguridad:
  * solo lo usa un administrador y hay que escribir BORRAR para confirmar;
  * antes de borrar se saca una copia completa de la base de datos (pg_dump); si la copia falla, NO se borra;
  * queda anotado en Auditoría qué se borró, quién y el nombre de la copia;
  * todo dentro de la empresa de la sesión: los clientes y productos se buscan con el filtro de empresa y lo
    demás se alcanza solo a partir de ellos.
"""

import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import Table, delete, func, or_, select, update
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registra todas las tablas en el metadata)
from app.core.config import get_settings
from app.db.base import Base
from app.models.client import Client
from app.models.invoice import Invoice
from app.models.notification import Notification
from app.models.product import Product
from app.models.project import Project
from app.models.quote import Quote, QuoteItem
from app.models.ticket import Ticket

logger = logging.getLogger("multitec.cleanup")

CONFIRM_WORD = "BORRAR"
MAX_PER_REQUEST = 500

# Nombres que suelen indicar datos de prueba. Solo sirve para marcarlos de antemano en la pantalla: la decisión
# final siempre es del administrador.
TEST_NAME = re.compile(
    r"\b(test|tests|testing|prueba|pruebas|verify|smoke|demo|ejemplo|ignorar|e2e|dummy|fake|borrar)\b", re.IGNORECASE
)

LABELS = {
    "clients": "Clientes",
    "projects": "Proyectos",
    "quotes": "Cotizaciones",
    "quote_items": "Partidas de cotización",
    "budgets": "Presupuestos",
    "invoices": "Facturas",
    "pre_invoices": "Prefacturas",
    "tickets": "Tickets",
    "visits": "Visitas",
    "surveys": "Levantamientos",
    "survey_assets": "Fotos y audios del levantamiento",
    "ticket_assets": "Fotos de tickets",
    "log_entries": "Entradas de bitácora",
    "client_assets": "Equipos instalados",
    "products": "Productos",
    "stock_movements": "Movimientos de inventario",
    "materials": "Materiales de proyecto",
}
# Lo que se muestra en el resumen (lo demás —historiales, índices de la IA— se borra igual, pero no se lista).
SUMMARY_TABLES = [
    "clients", "projects", "quotes", "budgets", "invoices", "tickets", "visits", "surveys",
    "survey_assets", "ticket_assets", "log_entries", "client_assets", "materials", "products", "stock_movements",
]


def looks_like_test(*texts: str | None) -> bool:
    return any(t and TEST_NAME.search(t) for t in texts)


def _references() -> dict[str, list[tuple[Table, Any]]]:
    refs: dict[str, list[tuple[Table, Any]]] = {}
    for table in Base.metadata.sorted_tables:
        for fk in table.foreign_keys:
            refs.setdefault(fk.column.table.name, []).append((table, fk.parent))
    return refs


class Plan:
    """Lo que se va a borrar, calculado sin tocar nada."""

    def __init__(self) -> None:
        self.ids: dict[str, set[Any]] = {}
        self.order: list[tuple[Table, Any, set[Any]]] = []  # (tabla, columna por la que se borra, valores)
        self.detach: list[tuple[Table, Any, set[Any]]] = []  # referencias opcionales que quedan en NULL

    def counts(self) -> dict[str, int]:
        return {name: len(ids) for name, ids in self.ids.items() if ids}


def _walk(db: Session, table: Table, ids: set[Any], plan: Plan, refs: dict[str, list[tuple[Table, Any]]]) -> None:
    for child, column in refs.get(table.name, []):
        if column.nullable:
            plan.detach.append((child, column, set(ids)))
            continue
        pk = list(child.primary_key.columns)
        if len(pk) == 1:
            found = {row[0] for row in db.execute(select(pk[0]).where(column.in_(ids)))}
            new = found - plan.ids.get(child.name, set())
            if new:
                plan.ids.setdefault(child.name, set()).update(new)
                _walk(db, child, new, plan, refs)
                plan.order.append((child, pk[0], new))
        else:
            # Tabla sin llave simple (índices de la IA): se borra directo por la columna que apunta al padre.
            plan.order.append((child, column, set(ids)))


def build_plan(db: Session, client_ids: list[int], product_ids: list[int]) -> tuple[Plan, list[Client], list[Product]]:
    if len(client_ids) + len(product_ids) > MAX_PER_REQUEST:
        raise ValueError(f"Elige como máximo {MAX_PER_REQUEST} registros por vez")
    # Con el filtro de empresa de la sesión: un id de otra empresa simplemente no aparece.
    clients = db.query(Client).filter(Client.id.in_(client_ids)).all() if client_ids else []
    products = db.query(Product).filter(Product.id.in_(product_ids)).all() if product_ids else []
    refs = _references()
    plan = Plan()
    for model, rows in ((Client, clients), (Product, products)):
        if not rows:
            continue
        table = model.__table__
        ids = {r.id for r in rows}
        plan.ids.setdefault(table.name, set()).update(ids)
        _walk(db, table, ids, plan, refs)
        plan.order.append((table, table.c.id, ids))
    return plan, clients, products


def describe(db: Session, plan: Plan, clients: list[Client], products: list[Product]) -> dict[str, Any]:
    counts = plan.counts()
    invoice_ids = plan.ids.get("invoices", set())
    ncf = []
    if invoice_ids:
        ncf = [
            {"code": code, "ncf": number, "voided": voided is not None}
            for code, number, voided in db.query(Invoice.code, Invoice.ncf, Invoice.voided_at)
            .filter(Invoice.id.in_(invoice_ids), Invoice.ncf.isnot(None))
            .order_by(Invoice.code)
        ]
    files = sum(len(_file_paths(db, plan, t)) for t in _file_tables(plan))
    return {
        "clients": [c.name for c in clients],
        "products": [p.name for p in products],
        "counts": [
            {"key": k, "label": LABELS.get(k, k), "count": counts[k]} for k in SUMMARY_TABLES if counts.get(k)
        ],
        "fiscal_invoices": ncf,
        "files": files,
    }


def _file_tables(plan: Plan) -> list[Table]:
    tables = {t.name: t for t, _c, _v in plan.order}
    return [t for name, t in tables.items() if "file_path" in t.c and plan.ids.get(name)]


def _file_paths(db: Session, plan: Plan, table: Table) -> list[str]:
    pk = list(table.primary_key.columns)
    if len(pk) != 1:
        return []
    ids = list(plan.ids.get(table.name, set()))
    if not ids:
        return []
    return [p for (p,) in db.execute(select(table.c.file_path).where(pk[0].in_(ids))) if p]


def backup_dir() -> Path:
    configured = get_settings().backup_dir
    return Path(configured).expanduser() if configured else Path.home() / "MultitecBackups"


def backup_database(label: str = "antes-de-borrar-pruebas") -> str | None:
    """Copia completa de la base de datos antes de borrar. Devuelve el nombre del archivo, o None cuando la base no es
    PostgreSQL (pruebas con SQLite). Si es PostgreSQL y la copia falla, lanza: sin copia no se borra nada."""
    settings = get_settings()
    url = make_url(settings.database_url)
    if not url.drivername.startswith("postgresql"):
        return None
    pg_dump = shutil.which("pg_dump") or str(Path(settings.pg_bin_path) / "pg_dump.exe")
    if not Path(pg_dump).exists() and not shutil.which(pg_dump):
        raise RuntimeError("No se encontró pg_dump para sacar la copia de seguridad; no se borró nada")
    folder = backup_dir()
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"multitec_{label}_{datetime.now():%Y-%m-%d_%H%M%S}.dump"
    env = {**os.environ, "PGPASSWORD": url.password or ""}
    command = [
        pg_dump, "-h", url.host or "127.0.0.1", "-p", str(url.port or 5432), "-U", url.username or "",
        "-d", url.database or "", "-F", "c", "-f", str(target),
    ]
    try:
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=600)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"No se pudo sacar la copia de seguridad ({exc}); no se borró nada") from None
    if result.returncode != 0 or not target.exists() or target.stat().st_size == 0:
        logger.error("pg_dump falló: %s", result.stderr[-500:])
        target.unlink(missing_ok=True)
        raise RuntimeError("No se pudo sacar la copia de seguridad; no se borró nada")
    return target.name


def execute(db: Session, plan: Plan) -> list[str]:
    """Borra según el plan (sin commit). Devuelve las rutas de archivos a eliminar del disco después del commit."""
    files = [p for t in _file_tables(plan) for p in _file_paths(db, plan, t)]
    # Primero se sueltan las referencias opcionales (también las de filas que luego se borran: es inofensivo y evita
    # depender del orden), después se borra de las hojas hacia la raíz.
    for table, column, ids in plan.detach:
        db.execute(update(table).where(column.in_(ids)).values({column.name: None}))
    for table, column, ids in plan.order:
        db.execute(delete(table).where(column.in_(ids)))
    project_ids = plan.ids.get("projects", set())
    if project_ids:
        # Los avisos de la campanita que apuntaban a esos proyectos ya no llevarían a ningún lado.
        patterns = [f"/proyectos/{pid}" for pid in project_ids]
        conditions = [Notification.link == p for p in patterns]
        conditions += [Notification.link.like(f"{p}?%") for p in patterns]
        conditions += [Notification.link.like(f"{p}/%") for p in patterns]
        for start in range(0, len(conditions), 300):
            db.query(Notification).filter(or_(*conditions[start : start + 300])).delete(synchronize_session=False)
    db.expire_all()
    return files


def remove_files(paths: list[str]) -> int:
    root = Path(get_settings().upload_dir).resolve()
    removed = 0
    for raw in paths:
        try:
            path = Path(raw).resolve()
            if root in path.parents and path.is_file():
                path.unlink()
                removed += 1
        except OSError:
            logger.warning("No se pudo borrar el archivo %s", raw)
    return removed


def candidates(db: Session) -> dict[str, Any]:
    """Clientes y productos con lo que tiene cada uno, y si su nombre parece de prueba."""
    projects = dict(db.query(Project.client_id, func.count(Project.id)).group_by(Project.client_id).all())
    quotes = dict(
        db.query(Project.client_id, func.count(Quote.id)).join(Quote, Quote.project_id == Project.id).group_by(Project.client_id).all()
    )
    invoices = dict(
        db.query(Project.client_id, func.count(Invoice.id)).join(Invoice, Invoice.project_id == Project.id).group_by(Project.client_id).all()
    )
    fiscal = dict(
        db.query(Project.client_id, func.count(Invoice.id))
        .join(Invoice, Invoice.project_id == Project.id)
        .filter(Invoice.ncf.isnot(None))
        .group_by(Project.client_id)
        .all()
    )
    tickets = dict(
        db.query(Project.client_id, func.count(Ticket.id)).join(Ticket, Ticket.project_id == Project.id).group_by(Project.client_id).all()
    )
    clients = [
        {
            "id": c.id,
            "name": c.name,
            "company": c.company,
            "created_at": c.created_at,
            "projects": projects.get(c.id, 0),
            "quotes": quotes.get(c.id, 0),
            "invoices": invoices.get(c.id, 0),
            "fiscal_invoices": fiscal.get(c.id, 0),
            "tickets": tickets.get(c.id, 0),
            "suspect": looks_like_test(c.name, c.company),
        }
        for c in db.query(Client).order_by(Client.created_at.desc(), Client.id.desc()).all()
    ]
    used = dict(
        db.query(QuoteItem.product_id, func.count(QuoteItem.id)).filter(QuoteItem.product_id.isnot(None)).group_by(QuoteItem.product_id).all()
    )
    products = [
        {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "price": float(p.price or 0),
            "used_in_quotes": used.get(p.id, 0),
            "suspect": looks_like_test(p.name),
        }
        for p in db.query(Product).order_by(Product.code).all()
    ]
    return {"clients": clients, "products": products, "confirm_word": CONFIRM_WORD}
