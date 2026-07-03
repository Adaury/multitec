import logging
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.cors import CORSMiddleware

from app.api.routers import (
    ai,
    auth,
    budgets,
    catalog,
    clients,
    engineering,
    execution,
    extensions,
    invoices,
    logbook,
    materials,
    ncf,
    projects,
    quotes,
    reports,
    surveys,
    tickets,
    users,
)
from app.core.config import INSECURE_DEFAULT_JWT_SECRET, get_settings
from app.core.limiter import limiter
from app.core.logging_config import configure_logging

configure_logging()
settings = get_settings()

logger = logging.getLogger("multitec")
if settings.jwt_secret == INSECURE_DEFAULT_JWT_SECRET:
    logger.warning(
        "JWT_SECRET sigue en su valor por defecto. Esto es aceptable para desarrollo "
        "local, pero NUNCA debe usarse en producción — cambia JWT_SECRET en backend/.env "
        "antes de desplegar (ver deploy/README.md)."
    )

app = FastAPI(title="Multitec ERP", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")

app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(projects.router)
app.include_router(surveys.router)
app.include_router(engineering.router)
app.include_router(catalog.router)
app.include_router(budgets.router)
app.include_router(quotes.router)
app.include_router(materials.router)
app.include_router(execution.router)
app.include_router(logbook.router)
app.include_router(invoices.router)
app.include_router(extensions.router)
app.include_router(tickets.router)
app.include_router(ai.router)
app.include_router(users.router)
app.include_router(ncf.router)
app.include_router(reports.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
