from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.security import require_role
from app.db.session import get_db
from app.models.budget import Budget, BudgetItem
from app.models.product import Product
from app.models.quote import Quote, QuoteHistory, QuoteItem
from app.schemas.budget import BudgetCreate, BudgetOut, BudgetUpdate
from app.schemas.quote import QuoteOut
from app.services.code_generator import next_code
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


@router.post("/api/projects/{project_id}/budgets", response_model=BudgetOut, status_code=status.HTTP_201_CREATED)
def create_budget(project_id: int, payload: BudgetCreate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    code = next_code(db, "PRE")
    budget = Budget(code=code, project_id=project_id, notes=payload.notes)
    _build_budget_items(db, budget, payload.items)

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    budget.total = round(sum(line_subtotal(l.quantity, l.unit_price) for l in lines), 2)

    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@router.get("/api/budgets/{budget_id}", response_model=BudgetOut)
def get_budget(budget_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    return budget


@router.put("/api/budgets/{budget_id}", response_model=BudgetOut)
def update_budget(budget_id: int, payload: BudgetUpdate, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    budget.notes = payload.notes
    budget.items.clear()
    db.flush()
    _build_budget_items(db, budget, payload.items)

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    budget.total = round(sum(line_subtotal(l.quantity, l.unit_price) for l in lines), 2)

    db.commit()
    db.refresh(budget)
    return budget


@router.post("/api/budgets/{budget_id}/convert-to-quote", response_model=QuoteOut, status_code=status.HTTP_201_CREATED)
def convert_to_quote(budget_id: int, db: Session = Depends(get_db), _=Depends(allowed_roles)):
    budget = db.query(Budget).options(joinedload(Budget.items)).filter(Budget.id == budget_id).one_or_none()
    if budget is None:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")

    settings = get_settings()
    code = next_code(db, "COT")
    quote = Quote(code=code, project_id=budget.project_id, source_budget_id=budget.id, notes=budget.notes)

    for item in budget.items:
        subtotal = line_subtotal(item.quantity, item.unit_price)
        quote.items.append(
            QuoteItem(
                product_id=item.product_id,
                description=item.description,
                quantity=item.quantity,
                unit_price=item.unit_price,
                subtotal=subtotal,
            )
        )

    lines = [LineInput(item.quantity, item.unit_price) for item in budget.items]
    quote.subtotal, quote.itbis, quote.total = compute_totals(lines, settings.itbis_rate)

    db.add(quote)
    db.flush()
    db.add(QuoteHistory(quote_id=quote.id, action="creada", note=f"Generada desde presupuesto {budget.code}"))
    db.commit()
    db.refresh(quote)
    return quote
