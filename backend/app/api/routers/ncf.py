from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.models.ncf_sequence import NcfSequence
from app.models.user import User
from app.schemas.ncf import NcfSequenceCreate, NcfSequenceOut, NcfSequenceUpdate

router = APIRouter(prefix="/api/ncf-sequences", tags=["ncf"])

admin_only = require_role("admin")


@router.get("", response_model=list[NcfSequenceOut])
def list_ncf_sequences(db: Session = Depends(get_db), _=Depends(admin_only)):
    return db.query(NcfSequence).order_by(NcfSequence.ncf_type, NcfSequence.expires_at).all()


@router.post("", response_model=NcfSequenceOut, status_code=status.HTTP_201_CREATED)
def create_ncf_sequence(
    payload: NcfSequenceCreate, db: Session = Depends(get_db), current_user: User = Depends(admin_only)
):
    sequence = NcfSequence(
        ncf_type=payload.ncf_type,
        description=payload.description,
        range_start=payload.range_start,
        range_end=payload.range_end,
        next_number=payload.range_start,
        expires_at=payload.expires_at,
        created_by=current_user.id,
    )
    db.add(sequence)
    db.commit()
    db.refresh(sequence)
    return sequence


@router.put("/{sequence_id}", response_model=NcfSequenceOut)
def update_ncf_sequence(
    sequence_id: int, payload: NcfSequenceUpdate, db: Session = Depends(get_db), _=Depends(admin_only)
):
    sequence = db.get(NcfSequence, sequence_id)
    if sequence is None:
        raise HTTPException(status_code=404, detail="Secuencia NCF no encontrada")
    sequence.active = payload.active
    db.commit()
    db.refresh(sequence)
    return sequence
