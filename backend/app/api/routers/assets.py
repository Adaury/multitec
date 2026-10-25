from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.client import Client
from app.models.client_asset import ClientAsset
from app.models.project import Project
from app.models.user import User
from app.schemas.client_asset import ClientAssetCreate, ClientAssetOut, ClientAssetUpdate
from app.services.audit import audit

router = APIRouter(tags=["assets"])

# Equipos instalados: el técnico los registra en campo (donde está el serial y la MAC); borrarlos es de oficina.
# Un técnico solo ve los de sus clientes (el parámetro client_id / client_asset_id pasa por services/access.py).
allowed_roles = require_role("admin", "oficina", "tecnico")
staff_roles = require_role("admin", "oficina")


def _check_project(db: Session, client_id: int, project_id: int | None) -> None:
    if project_id is None:
        return
    project = db.get(Project, project_id)
    if project is None or project.client_id != client_id:
        raise HTTPException(status_code=400, detail="Ese proyecto no es de este cliente")


@router.get("/api/clients/{client_id}/assets", response_model=list[ClientAssetOut])
def list_client_assets(client_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    rows = (
        db.query(ClientAsset)
        .filter(ClientAsset.client_id == client_id)
        .order_by(ClientAsset.location, ClientAsset.name, ClientAsset.id)
        .all()
    )
    return [ClientAssetOut.from_row(r) for r in rows]


@router.post("/api/clients/{client_id}/assets", response_model=ClientAssetOut, status_code=status.HTTP_201_CREATED)
def create_client_asset(
    client_id: int,
    payload: ClientAssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(allowed_roles),
):
    if db.get(Client, client_id) is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    _check_project(db, client_id, payload.project_id)
    row = ClientAsset(client_id=client_id, created_by=current_user.id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return ClientAssetOut.from_row(row)


@router.put("/api/client-assets/{client_asset_id}", response_model=ClientAssetOut)
def update_client_asset(
    client_asset_id: int, payload: ClientAssetUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)
):
    row = db.get(ClientAsset, client_asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data and not data["name"]:
        data.pop("name")  # el nombre nunca se borra
    if "kind" in data and data["kind"] is None:
        data.pop("kind")
    if "project_id" in data:
        _check_project(db, row.client_id, data["project_id"])
    for field, value in data.items():
        setattr(row, field, value)
    db.commit()
    db.refresh(row)
    return ClientAssetOut.from_row(row)


@router.delete("/api/client-assets/{client_asset_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client_asset(
    request: Request,
    client_asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(staff_roles),
):
    row = db.get(ClientAsset, client_asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    audit(
        db,
        "client_asset_deleted",
        user=current_user,
        entity="client_asset",
        entity_id=row.id,
        detail={"equipo": row.name, "serial": row.serial, "cliente_id": row.client_id},
        request=request,
    )
    db.delete(row)
    db.commit()
