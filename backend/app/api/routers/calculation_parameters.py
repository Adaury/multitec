from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai_engine.calculation import KNOWN_PARAMETERS
from app.core.security import require_role
from app.db.session import get_db
from app.models.calculation_parameter import CalculationParameter
from app.schemas.calculation_parameter import CalculationParameterOut, CalculationParameterUpsert

router = APIRouter(prefix="/api/calculation-parameters", tags=["calculation-parameters"])

allowed_roles = require_role("admin", "oficina")
admin_only = require_role("admin")


@router.get("", response_model=list[CalculationParameterOut])
def list_calculation_parameters(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    """Devuelve todas las claves conocidas (§ KNOWN_PARAMETERS), configuradas o no — una
    clave sin fila en `calculation_parameters` se muestra con su default de código para
    que el admin sepa qué valor está aplicando el cálculo hoy."""
    rows_by_key = {row.key: row for row in db.query(CalculationParameter).all()}
    result = []
    for key, meta in KNOWN_PARAMETERS.items():
        row = rows_by_key.get(key)
        result.append(
            CalculationParameterOut(
                key=key,
                value=float(row.value) if row is not None else meta["default"],
                description=(row.description if row is not None and row.description else meta["description"]),
                is_default=row is None,
                updated_at=row.updated_at if row is not None else None,
            )
        )
    return result


@router.put("/{key}", response_model=CalculationParameterOut)
def upsert_calculation_parameter(
    key: str, payload: CalculationParameterUpsert, db: Session = Depends(get_db), _=Depends(admin_only)
):
    if key not in KNOWN_PARAMETERS:
        raise HTTPException(status_code=404, detail=f"Parámetro desconocido: {key}")

    row = db.query(CalculationParameter).filter(CalculationParameter.key == key).one_or_none()
    if row is None:
        row = CalculationParameter(key=key, value=payload.value, description=payload.description)
        db.add(row)
    else:
        row.value = payload.value
        if payload.description is not None:
            row.description = payload.description

    db.commit()
    db.refresh(row)
    return CalculationParameterOut(
        key=row.key,
        value=float(row.value),
        description=row.description or KNOWN_PARAMETERS[key]["description"],
        is_default=False,
        updated_at=row.updated_at,
    )
