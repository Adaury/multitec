from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session, joinedload

from app.ai_engine.learning import record_budget_edit_feedback
from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.budget import Budget, BudgetItem
from app.models.product import Product
from app.models.project import Project
from app.models.quote import Quote, QuoteHistory, QuoteItem
from app.models.user import User
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.schemas.quote import QuoteOut
from app.services.code_generator import next_code
from app.services.notifications import notify_quote_pending
from app.services.pdf import build_budget_summary_pdf
from app.services.totals import LineInput, compute_totals, line_subtotal

router = APIRouter(tags=["budgets"])

allowed_roles = require_role("admin", "oficina")


def _resolve_item_fields(db: Session, product_id: int | None, description: str, unit_price: float) -> tuple[str, float]:
    """Si viene product_id y falta descripción/precio, los completa desde el catálogo."""
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None:
            raise HTTPException(status_code=400, detail=f"Producto {product_id} no encontrado")
        description = description or product.name
        if not unit_price:
            unit_price = float(product.price)
    return description, unit_price


def _build_budget_items(db: Session, budget: Budget, items_in) -> None:
    for item in items_in:
        description, unit_price = _resolve_item_fields(db, item.product_id, item.description, item.unit_price)
        budget.items.append(
            BudgetItem(
                product_id=item.product_id,
                description=description,
                quantity=item.quantity,
                unit_price=unit_price,
                note=item.note,
            )
        )


@router.get("/api/projects/{project_id}/budgets", response_model=list[BudgetOut])
def list_budgets(project_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return (
        db.query(Budget)
        .options(joinedload(Budget.items))
        .filter(Budget.project_id == project_id)
        .order_by(Budget.created_at.desc())
        .all()
    )


@router.get("/api/budgets", response_model=list[BudgetOut])
def list_all_budgets(db: Session = Depends(get_db), _=Depends(allowed_roles)):
    return db.query(Budget).options(joinedload(Budget.items)).order_by(Budget.created_at.desc()).all()


def build_budget(
    db: Session, project_id: int, notes: str | None, items_in, created_by: int | None, ai_generated: bool = False
) -> Budget:
    """Arma un Budget (+líneas +total) sin comitear — el caller decide cuándo. Compartida
    entre la creación manual (create_budget) y la generación automática desde el
    levantamiento (ver api/routers/ai.py). `ai_generated=True` solo lo pasa esta última —
    es lo que activa la captura de feedback en la primera edición humana (§ Motor 7, ver
    app.ai_engine.learning)."""
    code = next_code(db, "PRE")
    budget = Budget(code=code, project_id=project_id, notes=notes, created_by=created_by, ai_generated=ai_generated)
    _build_budget_items(db, budget, items_in)

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    budget.total = round(sum(line_subtotal(l.quantity, l.unit_price) for l in lines), 2)

    db.add(budget)
    return budget


@router.post("/api/projects/{project_id}/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(
    project_id: int, payload: BudgetCreate, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)
):
    budget = build_budget(db, project_id, payload.notes, payload.items, current_user.id)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/api/budgets/{budget_id}", response_model=BudgetOut)
def get_budget(budget_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget


@router.get("/api/budgets/{budget_id}/pdf")
def get_budget_pdf(budget_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = (
        db.query(Budget)
        .options(joinedload(Budget.items), joinedload(Budget.project).joinedload(Project.client))
        .filter(Budget.id == budget_id)
        .one_or_none()
    )
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    pdf_bytes = build_budget_summary_pdf(budget)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{budget.code}-resumen.pdf"'},
    )


@router.put("/api/budgets/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: int, payload: BudgetUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    new_items = [(item.product_id, item.description, item.quantity) for item in payload.items]
    record_budget_edit_feedback(db, budget.project_id, budget, new_items)

    budget.notes = payload.notes
    budget.items.clear()
    db.flush()
    _build_budget_items(db, budget, payload.items)

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    budget.total = round(sum(line_subtotal(l.quantity, l.unit_price) for l in lines), 2)

    db.commit()
    db.refresh(budget)
    return budget


def build_quote_from_budget(db: Session, budget: Budget, created_by: int | None) -> Quote:
    """Arma una Quote a partir de un Budget (copiando líneas, recalculando ITBIS) sin
    comitear — el caller decide cuándo. Compartida entre convert_to_quote (manual) y la
    generación automática desde el levantamiento (ver api/routers/ai.py). Requiere que
    `budget.id` ya exista (flush previo si el Budget se acaba de crear en la misma
    transacción)."""
    settings = get_settings()
    code = next_code(db, "COT")
    quote = Quote(
        code=code,
        project_id=budget.project_id,
        source_budget_id=budget.id,
        notes=budget.notes,
        created_by=created_by,
    )

    for item in budget.items:
        subtotal = line_subtotal(item.quantity, item.unit_price)
        quote.items.append(
            QuoteItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=subtotal,
                note=item.note,
            )
        )

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    quote.subtotal, quote.itbis, quote.total = compute_totals(lines, settings.itbis_rate)

    db.add(quote)
    db.flush()
    db.add(QuoteHistory(quote_id=quote.id, action="creada", note=f"Generada desde presupuesto {budget.code}"))
    return quote


@router.post("/api/budgets/{budget_id}/convert-to-quote", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def convert_to_quote(budget_id: int, db: Session = Depends(get_db), current_user: User = Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    quote = build_quote_from_budget(db, budget, current_user.id)
    db.commit()
    db.refresh(quote)
    notify_quote_pending(db, quote)
    return quote
