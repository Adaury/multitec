"""Activa el envío de correos con Gmail de forma segura.

Uso (desde la carpeta backend, en una terminal normal — NO a través de un chat, porque la
contraseña no debe quedar escrita en ningún lado):

    venv\\Scripts\\python.exe scripts\\setup_smtp.py

Qué hace:
  1. Pide la "contraseña de aplicación" de Google (se teclea sin mostrarse).
  2. Se conecta a smtp.gmail.com y envía un correo de PRUEBA a NOTIFICATION_EMAIL.
  3. Solo si la prueba sale bien, escribe SMTP_HOST y SMTP_PASSWORD en backend/.env.
     Si falla, no cambia nada (así la app nunca queda esperando a un SMTP que no responde).

Cómo sacar la contraseña de aplicación: cuenta de Google -> Seguridad -> Verificación en dos pasos
(debe estar activada) -> Contraseñas de aplicaciones -> crear una llamada "Multitec".
"""

import getpass
import re
import smtplib
import sys
from email.message import EmailMessage
from pathlib import Path

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
GMAIL_HOST = "smtp.gmail.com"


def read_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def set_env_values(text: str, updates: dict[str, str]) -> str:
    """Reemplaza (o agrega al final) cada clave conservando el resto del archivo y sus saltos de línea."""
    newline = "\r\n" if "\r\n" in text else "\n"
    for key, value in updates.items():
        # [^\r\n]* y no .*: el punto se comeria el \r y el archivo quedaria con saltos de linea mezclados.
        pattern = re.compile(rf"(?m)^{re.escape(key)}=[^\r\n]*")
        if pattern.search(text):
            text = pattern.sub(lambda _m, k=key, v=value: f"{k}={v}", text)
        else:
            text = text.rstrip("\r\n") + newline + f"{key}={value}" + newline
    return text


def send_test(user: str, password: str, sender: str, to: str, port: int = 587) -> None:
    msg = EmailMessage()
    msg["Subject"] = "Multitec: prueba de correo"
    msg["From"] = sender
    msg["To"] = to
    msg.set_content(
        "Este es un correo de prueba de Multitec.\n\n"
        "Si lo recibes, las alertas (cotización pendiente, ticket asignado, factura emitida) "
        "llegarán a esta dirección."
    )
    with smtplib.SMTP(GMAIL_HOST, port, timeout=20) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def main() -> int:
    if not ENV_PATH.exists():
        print(f"No se encontró {ENV_PATH}")
        return 1
    text = ENV_PATH.read_text(encoding="utf-8")
    env = read_env(text)
    user = env.get("SMTP_USER", "")
    sender = env.get("SMTP_FROM") or user
    to = env.get("NOTIFICATION_EMAIL") or user
    if not user:
        print("Falta SMTP_USER en backend/.env (tu correo de Gmail).")
        return 1

    print(f"Correo remitente: {user}")
    print(f"Las alertas llegarán a: {to}")
    password = getpass.getpass("Contraseña de aplicación de Google (no se muestra): ").replace(" ", "")
    if not password:
        print("No escribiste nada; no se cambió nada.")
        return 1

    try:
        send_test(user, password, sender, to)
    except smtplib.SMTPAuthenticationError:
        print(
            "\nGoogle rechazó la contraseña. Revisa que:\n"
            "  - sea una CONTRASEÑA DE APLICACIÓN (16 letras), no la contraseña normal de la cuenta,\n"
            "  - la verificación en dos pasos esté activada en la cuenta de Google.\n"
            "No se cambió nada."
        )
        return 2
    except Exception as exc:  # red caída, puerto bloqueado, etc.
        print(f"\nNo se pudo enviar el correo de prueba ({type(exc).__name__}: {exc}). No se cambió nada.")
        return 3

    ENV_PATH.write_text(
        set_env_values(text, {"SMTP_HOST": GMAIL_HOST, "SMTP_PASSWORD": password}),
        encoding="utf-8",
        newline="",
    )
    print(f"\n✅ Listo: te envié un correo de prueba a {to} y activé el envío de alertas.")
    print("Reinicia el backend para que tome el cambio (cierra y abre la ventana 'Multitec - Backend').")
    return 0


if __name__ == "__main__":
    sys.exit(main())
