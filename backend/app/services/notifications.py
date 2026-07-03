from sqlalchemy.orm import Session

from app.models.invoice import Invoice
from app.models.quote import Quote
from app.models.ticket import Ticket
from app.models.user import User
from app.services import email
from app.services.pdf import build_invoice_pdf


def notify_quote_pending(db: Session, quote: Quote) -> None:
    """Avisa a los admins activos que hay una cotización nueva esperando decisión."""
    admins = db.query(User).filter(User.role == "admin", User.is_active.is_(True)).all()
    subject = f"Cotización {quote.code} pendiente de aprobar"
    body = (
        "Hay una cotización nueva pendiente de decisión.\n\n"
        f"Código: {quote.code}\n"
        f"Proyecto: {quote.project.code} — {quote.project.client.name}\n"
        f"Total: RD$ {float(quote.total):,.2f}\n"
    )
    for admin in admins:
        email.send_email(admin.email, subject, body)


def notify_ticket_assigned(db: Session, ticket: Ticket) -> None:
    """Avisa al técnico que se le acaba de asignar un ticket."""
    if ticket.technician_id is None:
        return
    technician = db.get(User, ticket.technician_id)
    if technician is None:
        return
    subject = f"Ticket {ticket.code} asignado"
    body = (
        "Se te asignó un ticket de soporte.\n\n"
        f"Código: {ticket.code}\n"
        f"Proyecto: {ticket.project.code}\n"
        f"Problema: {ticket.problem}\n"
    )
    email.send_email(technician.email, subject, body)


def notify_invoice_issued(invoice: Invoice) -> None:
    """Envía al correo del cliente (si tiene uno registrado) la factura recién emitida,
    con el PDF adjunto — si no tiene correo, simplemente no hay a quién avisar."""
    client = invoice.project.client
    if not client.email:
        return
    subject = f"Factura {invoice.code} emitida"
    body = (
        "Se emitió tu factura.\n\n"
        f"Código: {invoice.code}\n"
        f"NCF: {invoice.ncf or '—'}\n"
        f"Total: RD$ {float(invoice.total):,.2f}\n\n"
        "Adjuntamos el PDF de la factura."
    )
    pdf_bytes = build_invoice_pdf(invoice)
    email.send_email(
        client.email, subject, body, attachment=(f"{invoice.code}.pdf", pdf_bytes, "application/pdf")
    )
