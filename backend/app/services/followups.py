from datetime import date, timedelta
from urllib.parse import quote as url_quote

from sqlalchemy.orm import Session, joinedload

from app.core.config import get_settings
from app.core.timeutil import to_local, today_dr
from app.models.invoice import Invoice
from app.models.project import Project
from app.models.quote import Quote
from app.schemas.followup import FollowupInvoice, FollowupQuote, FollowupsOut
from app.services.company import get_company

# Una cotización recién enviada no se persigue: se lista cuando lleva al menos esto sin respuesta.
QUOTE_FOLLOWUP_AFTER_DAYS = 3


def whatsapp_link(phone: str | None, message: str) -> str | None:
    """Enlace wa.me con el mensaje ya escrito. Teléfono dominicano de 10 dígitos (o 11 con el 1);
    cualquier otro formato no se adivina: sin enlace."""
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if len(digits) == 10:
        digits = "1" + digits
    elif not (len(digits) == 11 and digits.startswith("1")):
        return None
    return f"https://wa.me/{digits}?text={url_quote(message)}"


def _money(value: float) -> str:
    return f"RD$ {value:,.2f}"


def _short(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def invoice_message(company: str, client: str, code: str, ncf: str | None, total: float, due_on: date, days_overdue: int) -> str:
    ref = f"{code}" + (f" (NCF {ncf})" if ncf else "")
    if days_overdue > 0:
        body = (
            f"le escribimos de {company} sobre la factura {ref} por {_money(total)}, que venció el {_short(due_on)} "
            f"({days_overdue} día{'s' if days_overdue != 1 else ''} de atraso). "
            "¿Nos puede confirmar la fecha en que podrá realizar el pago?"
        )
    else:
        body = (
            f"le escribimos de {company} para recordarle la factura {ref} por {_money(total)}, "
            f"con vencimiento el {_short(due_on)}. Quedamos atentos a su pago."
        )
    return f"Buen día, {client}. {body} Gracias por su confianza."


def quote_message(company: str, client: str, code: str, total: float, sent_on: date) -> str:
    return (
        f"Buen día, {client}. Le escribimos de {company} para dar seguimiento a la cotización {code} "
        f"por {_money(total)} que le enviamos el {_short(sent_on)}. ¿Pudo revisarla? "
        "Con gusto resolvemos cualquier duda o la ajustamos a lo que necesite."
    )


def build_followups(db: Session) -> FollowupsOut:
    settings = get_settings()
    company = get_company(db).name
    today = today_dr()

    receivables: list[FollowupInvoice] = []
    invoices = (
        db.query(Invoice)
        .options(joinedload(Invoice.project).joinedload(Project.client))
        .filter(Invoice.voided_at.is_(None), Invoice.paid_at.is_(None), Invoice.total > 0)
        .all()
    )
    for invoice in invoices:
        client = invoice.project.client
        issued_on = to_local(invoice.created_at).date()
        due_on = issued_on + timedelta(days=settings.invoice_due_days)
        days_overdue = (today - due_on).days
        total = float(invoice.total)
        message = invoice_message(company, client.name, invoice.code, invoice.ncf, total, due_on, days_overdue)
        receivables.append(
            FollowupInvoice(
                invoice_id=invoice.id,
                project_id=invoice.project_id,
                code=invoice.code,
                ncf=invoice.ncf,
                client_name=client.name,
                client_phone=client.phone,
                total=total,
                issued_on=issued_on,
                due_on=due_on,
                days_overdue=days_overdue,
                overdue=days_overdue > 0,
                message=message,
                whatsapp_url=whatsapp_link(client.phone, message),
            )
        )
    # Lo más atrasado primero.
    receivables.sort(key=lambda r: (-r.days_overdue, r.code))

    waiting: list[FollowupQuote] = []
    quotes = (
        db.query(Quote)
        .options(joinedload(Quote.project).joinedload(Project.client))
        .filter(Quote.status == "pendiente")
        .all()
    )
    for quote in quotes:
        sent_on = to_local(quote.created_at).date()
        days_waiting = (today - sent_on).days
        if days_waiting < QUOTE_FOLLOWUP_AFTER_DAYS:
            continue
        client = quote.project.client
        total = float(quote.total)
        message = quote_message(company, client.name, quote.code, total, sent_on)
        waiting.append(
            FollowupQuote(
                quote_id=quote.id,
                project_id=quote.project_id,
                code=quote.code,
                client_name=client.name,
                client_phone=client.phone,
                total=total,
                sent_on=sent_on,
                days_waiting=days_waiting,
                stale=days_waiting >= settings.quote_stale_days,
                message=message,
                whatsapp_url=whatsapp_link(client.phone, message),
            )
        )
    waiting.sort(key=lambda q: (-q.days_waiting, q.code))

    overdue = [r for r in receivables if r.overdue]
    return FollowupsOut(
        receivables_total=round(sum(r.total for r in receivables), 2),
        overdue_total=round(sum(r.total for r in overdue), 2),
        overdue_count=len(overdue),
        receivables=receivables,
        quotes=waiting,
    )
