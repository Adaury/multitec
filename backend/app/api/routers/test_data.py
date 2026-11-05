"""Administración → Borrar datos de prueba. Solo administradores."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.user import User
from app.services import data_cleanup
from app.services.audit import audit

router = APIRouter(prefix="/api/admin/test-data", tags=["admin"])

admin_only = require_role("admin")


class Selection(BaseModel):
    client_ids: list[int] = Field(default_factory=list, max_length=data_cleanup.MAX_PER_REQUEST)
    product_ids: list[int] = Field(default_factory=list, max_length=data_cleanup.MAX_PER_REQUEST)


class DeleteRequest(Selection):
    confirm: str = ""


@router.get("")
def list_candidates(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return data_cleanup.candidates(db)


@router.post("/preview")
def preview(payload: Selection, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    try:
        plan, clients, products = data_cleanup.build_plan(db, payload.client_ids, payload.product_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return data_cleanup.describe(db, plan, clients, products)


@router.post("/delete")
def delete_selected(
    request: Request, payload: DeleteRequest, db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    if payload.confirm.strip().upper() != data_cleanup.CONFIRM_WORD:
        raise HTTPException(status_code=400, detail=f"Escribe {data_cleanup.CONFIRM_WORD} para confirmar")
    try:
        plan, clients, products = data_cleanup.build_plan(db, payload.client_ids, payload.product_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    if not clients and not products:
        raise HTTPException(status_code=400, detail="No elegiste nada para borrar")

    summary = data_cleanup.describe(db, plan, clients, products)
    try:
        backup = data_cleanup.backup_database()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from None

    files = data_cleanup.execute(db, plan)
    audit(
        db,
        "test_data.delete",
        user=current_user,
        entity="test_data",
        detail={
            "clientes": summary["clients"][:100],
            "productos": summary["products"][:100],
            "cantidades": {c["label"]: c["count"] for c in summary["counts"]},
            "facturas_con_ncf": [f["ncf"] for f in summary["fiscal_invoices"]],
            "copia": backup,
        },
        request=request,
    )
    db.commit()
    removed = data_cleanup.remove_files(files)
    return {**summary, "backup": backup, "files_removed": removed}
