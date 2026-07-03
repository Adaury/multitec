from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.client import Client
from app.models.user import User
from app.schemas.client import ClientCreate, ClientOut, ClientUpdate
from app.services.csv_export import build_csv

router = APIRouter(prefix="/api/clients", tags=["clients"])

# admin y oficina pueden gestionar clientes; técnico solo puede consultarlos.
allowed_roles = require_role("admin", "oficina", "tecnico")
write_roles = require_role("admin", "oficina")


@router.get("", response_model=list[ClientOut])
def list_clients(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Client).order_by(Client.name).all()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(payload: ClientCreate, db: Session = Depends(get_db), current_user: User = Depends(write_roles)):
    client = Client(**payload.model_dump(), created_by=current_user.id)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/export")
def export_clients_csv(db: Session = Depends(get_db), _=Depends(write_roles)):
    clients = db.query(Client).order_by(Client.name).all()
    headers = ["Código", "Nombre", "Empresa", "RNC", "Teléfono", "Correo", "Dirección"]
    rows = [
        [c.id, c.name, c.company or "", c.rnc or "", c.phone or "", c.email or "", c.address or ""]
        for c in clients
    ]
    csv_bytes = build_csv(headers, rows)
    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="clientes.csv"'},
    )


@router.get("/{client_id}", response_model=ClientOut)
def get_client(client_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    return client


@router.put("/{client_id}", response_model=ClientOut)
def update_client(client_id: int, payload: ClientUpdate, db: Session = Depends(get_db), _=Depends(write_roles)):
    client = db.get(Client, client_id)
    if client is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    for field, value in payload.model_dump().items():
        setattr(client, field, value)
    db.commit()
    db.refresh(client)
    return client
