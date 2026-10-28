import logging
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.responses import FileResponse, JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.api.routers import (
    ai,
    ai_feedback_events,
    assets,
    assistant,
    audit,
    auth,
    budgets,
    calculation_parameters,
    catalog,
    categories,
    clients,
    company,
    engineering,
    execution,
    extensions,
    followups,
    client_errors,
    comparisons,
    generation,
    geo,
    inventory,
    invoices,
    logbook,
    materials,
    ncf,
    notifications,
    platform,
    projects,
    public,
    purchase_invoices,
    quotes,
    reports,
    search,
    suppliers,
    surveys,
    system,
    tickets,
    users,
    visits,
)
from app.core.config import INSECURE_DEFAULT_JWT_SECRET, get_settings
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.core.logging_config import configure_logging
from app.db.tenant import TenantReferenceError
from app.models.user import User
from app.services.uploads import can_read_upload

configure_logging()
settings = get_settings()

logger = logging.getLogger("multitec")
if settings.jwt_secret == INSECURE_DEFAULT_JWT_SECRET:
    if settings.environment == "production":
        # El secreto por defecto es público en el código fuente — con ENVIRONMENT=production
        # y este valor, cualquiera podría forjar un JWT válido para cualquier usuario. Mejor
        # no arrancar que arrancar inseguro.
        raise RuntimeError(
            "JWT_SECRET sigue en su valor por defecto con ENVIRONMENT=production. "
            "Cambia JWT_SECRET en backend/.env antes de desplegar (ver deploy/README.md)."
        )
    logger.warning(
        "JWT_SECRET sigue en su valor por defecto. Esto es aceptable para desarrollo "
        "local, pero NUNCA debe usarse en producción — cambia JWT_SECRET en backend/.env "
        "antes de desplegar (ver deploy/README.md)."
    )

app = FastAPI(
    title="Multitec ERP",
    version="0.1.0",
    docs_url="/docs" if settings.enable_docs else None,
    redoc_url="/redoc" if settings.enable_docs else None,
    openapi_url="/openapi.json" if settings.enable_docs else None,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(TenantReferenceError)
async def tenant_reference_handler(request: Request, exc: TenantReferenceError) -> JSONResponse:
    """Algo apuntaba a un registro de otra empresa (o inexistente): para quien llama es un «no encontrado»."""
    logger.warning("Referencia a otra empresa rechazada en %s %s: %s", request.method, request.url.path, exc)
    return JSONResponse(status_code=status.HTTP_404_NOT_FOUND, content={"detail": "No encontrado"})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Red de seguridad: cualquier excepción no manejada se registra en el log del
    servidor con el traceback completo, pero al cliente solo le llega un mensaje
    genérico — nunca detalles internos (rutas, queries, stack traces)."""
    logger.exception("Error no manejado en %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Ocurrió un error interno. Si persiste, contacta al administrador."},
    )

@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Cabeceras que van aunque alguien llegue a la API sin pasar por Caddy o Vite (puerto 8000 directo,
    túnel). Las respuestas de /api llevan datos de clientes y facturas: no-store evita que el navegador o un
    proxy las guarde (un iPhone compartido, por ejemplo). Lo que ya trae su propia política (/uploads) se respeta."""
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    if request.url.path.startswith("/api/"):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    # Lista explícita en vez de "*": con credenciales (cookie del refresh token) conviene decir qué se acepta.
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)


@app.get("/uploads/{file_path:path}", include_in_schema=False)
def get_upload(file_path: str, user: User = Depends(get_current_user)):
    """Fotos y audios del trabajo: solo con sesión. Antes eran un directorio público y cualquiera con
    el enlace (reenviado por WhatsApp, por ejemplo) los veía. Los nombres son aleatorios, pero un
    enlace filtrado no debe bastar. Además, cada empresa solo ve los archivos de su carpeta."""
    root = Path(settings.upload_dir).resolve()
    target = (root / file_path).resolve()
    if root not in target.parents or not target.is_file():
        raise HTTPException(status_code=404, detail="Archivo no encontrado")
    if not can_read_upload(user.company_id, target.relative_to(root).as_posix()):
        raise HTTPException(status_code=404, detail="Archivo no encontrado")  # 404: no revela que existe
    # Nunca se interpretan como otra cosa que lo que son (ver services/uploads.py).
    return FileResponse(
        target,
        headers={
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; img-src 'self'; media-src 'self'; sandbox",
            "Cache-Control": "private, max-age=3600",
        },
    )


app.include_router(auth.router)
app.include_router(audit.router)
app.include_router(assets.router)
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(surveys.router)
app.include_router(engineering.router)
app.include_router(catalog.router)
app.include_router(categories.router)
app.include_router(inventory.router)
app.include_router(budgets.router)
app.include_router(calculation_parameters.router)
app.include_router(quotes.router)
app.include_router(materials.router)
app.include_router(execution.router)
app.include_router(logbook.router)
app.include_router(invoices.router)
app.include_router(extensions.router)
app.include_router(tickets.router)
app.include_router(ai.router)
app.include_router(ai_feedback_events.router)
app.include_router(users.router)
app.include_router(platform.router)
app.include_router(generation.router)
app.include_router(comparisons.router)
app.include_router(client_errors.router)
app.include_router(geo.router)
app.include_router(ncf.router)
app.include_router(company.router)
app.include_router(followups.router)
app.include_router(reports.router)
app.include_router(search.router)
app.include_router(notifications.router)
app.include_router(visits.router)
app.include_router(assistant.router)
app.include_router(system.router)
app.include_router(public.router)
app.include_router(suppliers.router)
app.include_router(purchase_invoices.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
