from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import require_role
from app.db.session import get_db
from app.schemas.search import SearchResults
from app.services.search import global_search

router = APIRouter(prefix="/api/search", tags=["search"])

allowed_roles = require_role("admin", "oficina", "tecnico")


@router.get("", response_model=SearchResults)
def search(q: str = "", db: Session = Depends(get_db), _=Depends(allowed_roles)):
    if len(q.strip()) < 2:
        return {"clients": [], "projects": [], "tickets": []}
    return global_search(db, q.strip())
