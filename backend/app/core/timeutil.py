from datetime import date, datetime, timedelta, timezone

# Hora de República Dominicana: UTC-4 todo el año (sin horario de verano). Fijo en vez de
# zoneinfo porque en Windows requiere el paquete tzdata.
DR_TZ = timezone(timedelta(hours=-4))


def to_local(value: datetime) -> datetime:
    """Los created_at se guardan en UTC (SQLite los devuelve naive); la fecha de negocio
    es la dominicana — de noche difiere en un día de la UTC."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(DR_TZ)


def today_dr() -> date:
    """'Hoy' en hora dominicana, independiente de la zona horaria del servidor."""
    return datetime.now(DR_TZ).date()
