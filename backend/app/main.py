from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
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
    projects,
    quotes,
    surveys,
    tickets,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title="Multitec ERP", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


@app.get("/api/health")
def health():
    return {"status": "ok"}
