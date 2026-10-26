from sqlalchemy import create_engine, event
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import Session, sessionmaker, with_loader_criteria

from sqlalchemy.sql.util import find_tables

from app.core.config import get_settings
from app.db.base import Base
from app.db.tenant import TenantContextError, TenantMixin

settings = get_settings()

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
# pool_pre_ping: prueba la conexión antes de usarla, así un reinicio o caída de la base no
# le devuelve un error interno al primer usuario con conexiones muertas del pool.
engine = create_engine(settings.database_url, connect_args=connect_args, pool_pre_ping=True)


_TENANT_TABLES: set[str] = set()


def _tenant_table_names() -> set[str]:
    if not _TENANT_TABLES:
        _TENANT_TABLES.update(m.class_.__table__.name for m in Base.registry.mappers if issubclass(m.class_, TenantMixin))
    return _TENANT_TABLES


def _touches_tenant_table(statement) -> bool:
    tables = find_tables(statement, check_columns=True, include_aliases=True, include_joins=True, include_selects=True)
    return any(getattr(table, "name", None) in _tenant_table_names() for table in tables)


class TenantSession(Session):
    """Sesión que sabe de qué empresa es y no deja ver ni escribir datos de otra (ver app/db/tenant.py).

    La empresa va en `info["company_id"]`; `get_current_user` la fija al autenticar. `info["bypass_tenant"]` apaga el
    filtro (login, panel de plataforma, scripts)."""

    def __init__(self, *args, company_id: int | None = None, bypass_tenant: bool = False, **kwargs):
        super().__init__(*args, **kwargs)
        self.info["company_id"] = company_id
        self.info["bypass_tenant"] = bypass_tenant

    def get(self, entity, ident, *args, **kwargs):
        # El identity map puede devolver un objeto ya cargado sin ejecutar SQL (y por tanto sin filtro): se revisa aquí.
        return _visible(self, super().get(entity, ident, *args, **kwargs))


def _visible(session: Session, obj):
    if obj is None or not isinstance(obj, TenantMixin) or session.info.get("bypass_tenant"):
        return obj
    company_id = session.info.get("company_id")
    if company_id is None:
        raise TenantContextError("Consulta de datos de empresa sin empresa activa en la sesión")
    return obj if obj.company_id == company_id else None


@event.listens_for(TenantSession, "do_orm_execute")
def _scope_to_company(state) -> None:
    # Las cargas de columnas y de relaciones heredan el filtro de la consulta que las originó.
    if state.is_column_load or state.is_relationship_load:
        return
    if not (state.is_select or state.is_update or state.is_delete):
        return
    session = state.session
    if session.info.get("bypass_tenant"):
        return
    # `all_mappers` no ve el modelo en `select(func.count()).select_from(Modelo)` ni en `Query.count()` (no hay columnas
    # de la entidad): se miran también las tablas del statement, subconsultas incluidas.
    if not (
        any(issubclass(mapper.class_, TenantMixin) for mapper in state.all_mappers)
        or _touches_tenant_table(state.statement)
    ):
        return
    company_id = session.info.get("company_id")
    if company_id is None:
        # Falla cerrado: sin empresa nunca se devuelve "todo".
        raise TenantContextError("Consulta de datos de empresa sin empresa activa en la sesión")
    state.statement = state.statement.options(
        with_loader_criteria(TenantMixin, lambda cls: cls.company_id == company_id, include_aliases=True)
    )


@event.listens_for(TenantSession, "before_flush")
def _stamp_company(session, flush_context, instances) -> None:
    bypass = session.info.get("bypass_tenant", False)
    company_id = session.info.get("company_id")

    for obj in list(session.new):
        if not isinstance(obj, TenantMixin):
            continue
        nullable = type(obj).__table__.c.company_id.nullable
        if obj.company_id is None:
            if bypass or company_id is None:
                if nullable:
                    continue  # p. ej. un intento de acceso fallido en la auditoría: no hay empresa
                raise TenantContextError(f"{type(obj).__name__} se creó sin empresa")
            obj.company_id = company_id
        elif not bypass and obj.company_id != company_id:
            raise TenantContextError(f"{type(obj).__name__} es de otra empresa")

    if bypass:
        return
    for obj in list(session.dirty):
        if isinstance(obj, TenantMixin):
            if sa_inspect(obj).attrs.company_id.history.has_changes():
                raise TenantContextError(f"No se puede cambiar la empresa de un {type(obj).__name__}")
    for obj in list(session.deleted):
        if isinstance(obj, TenantMixin) and obj.company_id != company_id:
            raise TenantContextError(f"{type(obj).__name__} es de otra empresa")


SessionLocal = sessionmaker(class_=TenantSession, autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
