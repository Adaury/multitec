from datetime import date, datetime, timedelta, timezone

# Hora de República Dominicana: UTC-4 todo el año (sin horario de verano). Fijo en vez de
# zoneinfo porque en Windows requiere el paquete tzdata.
DR_TZ = timezone(timedelta(hours=-4))


def as_utc(value: datetime) -> datetime:
    """SQLite devuelve los DateTime sin zona aunque la columna sea timezone=True (Postgres sí
    la conserva); lo guardado es siempre UTC. Se normaliza antes de comparar o restar."""
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def to_local(value: datetime) -> datetime:
    """Los created_at se guardan en UTC (SQLite los devuelve naive); la fecha de negocio
    es la dominicana — de noche difiere en un día de la UTC."""
    return as_utc(value).astimezone(DR_TZ)


def today_dr() -> date:
    """'Hoy' en hora dominicana, independiente de la zona horaria del servidor."""
    return datetime.now(DR_TZ).date()
