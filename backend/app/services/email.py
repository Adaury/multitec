import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger("multitec.email")


def send_email(to: str, subject: str, body: str, attachment: tuple[str, bytes, str] | None = None) -> None:
    """Envío best-effort: nunca lanza — un SMTP caído no debe tumbar la operación
    principal (crear cotización, asignar ticket, emitir factura). Sin SMTP_HOST
    configurado, solo registra el correo en el log (modo consola, útil en desarrollo).

    `attachment`, si se da, es (filename, content, mime_type) — p. ej.
    ("FAC-000001.pdf", pdf_bytes, "application/pdf").
    """
    settings = get_settings()

    if not settings.smtp_host:
        logger.info("EMAIL (modo consola, SMTP_HOST no configurado) to=%s subject=%s\n%s", to, subject, body)
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(body)

    if attachment:
        filename, content, mime_type = attachment
        maintype, _, subtype = mime_type.partition("/")
        msg.add_attachment(content, maintype=maintype, subtype=subtype or "octet-stream", filename=filename)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception:
        logger.exception("Error enviando correo a %s (asunto: %s)", to, subject)
