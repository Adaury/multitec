from datetime import date

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.ncf_sequence import NcfSequence


def default_ncf_type(client: Client) -> str:
    """B01 (crédito fiscal) si el cliente tiene RNC, B02 (consumo) para consumidor final."""
    return "B01" if client.rnc else "B02"


def assign_ncf(db: Session, ncf_type: str) -> tuple[str, str]:
    """Toma el siguiente número de una secuencia NCF activa y vigente para `ncf_type`,
    lo consume (avanza `next_number`) y devuelve (ncf, ncf_type). No hace commit — el
    caller decide cuándo persistir junto con el resto de la factura."""
    sequence = db.execute(
        select(NcfSequence)
        .where(
            NcfSequence.ncf_type == ncf_type,
            NcfSequence.active.is_(True),
            NcfSequence.expires_at >= date.today(),
            NcfSequence.next_number <= NcfSequence.range_end,
        )
        .order_by(NcfSequence.expires_at)
        .limit(1)
        .with_for_update()
    ).scalar_one_or_none()

    if sequence is None:
        raise HTTPException(
            status_code=400,
            detail=(
                f"No hay una secuencia NCF activa y vigente para el tipo {ncf_type}. "
                "Registra un nuevo rango autorizado por la DGII en Configuración > NCF."
            ),
        )

    ncf = f"{ncf_type}{sequence.next_number:08d}"
    sequence.next_number += 1
    return ncf, ncf_type
