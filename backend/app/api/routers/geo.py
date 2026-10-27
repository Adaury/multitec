"""Convierte una dirección escrita en coordenadas, para poder mostrar el mapa del proyecto.

Google cerró su mapa incrustado gratuito (responde 404), así que las direcciones sin coordenadas se ubican con
OpenStreetMap (Nominatim, gratis y sin clave) y se muestran en su mapa. La dirección del cliente sale del servidor
hacia Nominatim: solo ella, sin nombres ni más datos. Se guarda en memoria lo ya buscado para no repetir consultas
(Nominatim pide máximo 1 por segundo)."""

import logging
import threading
import time
from collections import OrderedDict

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request

from app.core.limiter import limiter
from app.core.security import get_current_user
from app.models.user import User

logger = logging.getLogger("multitec.geo")

router = APIRouter(prefix="/api/geo", tags=["geo"])

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
# Nominatim exige identificar la aplicación en el User-Agent.
USER_AGENT = "Multitec-ERP/1.0 (+https://github.com/Adaury/multitec)"
_CACHE_MAX = 500
_FOUND_TTL = 30 * 24 * 3600
_MISSING_TTL = 6 * 3600

_cache: "OrderedDict[str, tuple[float, dict | None]]" = OrderedDict()
_lock = threading.Lock()
_call_lock = threading.Lock()  # espacia las consultas a Nominatim sin frenar la lectura del caché
_last_call = 0.0


def reset_cache() -> None:
    with _lock:
        _cache.clear()


def _lookup(query: str) -> dict | None:
    """Una consulta a Nominatim, primero acotada a República Dominicana y luego sin acotar."""
    global _last_call
    for country in ("do", None):
        with _call_lock:  # a lo sumo una consulta por segundo
            wait = 1.0 - (time.monotonic() - _last_call)
            if wait > 0:
                time.sleep(wait)
            _last_call = time.monotonic()
        params = {"q": query, "format": "jsonv2", "limit": 1}
        if country:
            params["countrycodes"] = country
        response = httpx.get(NOMINATIM_URL, params=params, headers={"User-Agent": USER_AGENT}, timeout=6.0)
        response.raise_for_status()
        results = response.json()
        if results:
            return {
                "lat": float(results[0]["lat"]),
                "lng": float(results[0]["lon"]),
                "display_name": results[0].get("display_name", ""),
            }
    return None


@router.get("/search")
@limiter.limit("30/minute")
def search_address(
    request: Request,
    q: str = Query(min_length=5, max_length=300),
    _: User = Depends(get_current_user),
):
    key = " ".join(q.lower().split())
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and hit[0] > now:
            _cache.move_to_end(key)
            found = hit[1]
            if found is None:
                raise HTTPException(status_code=404, detail="No se encontró esa dirección en el mapa")
            return found
    try:
        found = _lookup(key)
    except (httpx.HTTPError, ValueError, KeyError):
        logger.warning("No se pudo consultar Nominatim para una dirección", exc_info=True)
        raise HTTPException(status_code=503, detail="El mapa no está disponible ahora. Usa «Cómo llegar».")
    with _lock:
        _cache[key] = (now + (_FOUND_TTL if found else _MISSING_TTL), found)
        while len(_cache) > _CACHE_MAX:
            _cache.popitem(last=False)
    if found is None:
        raise HTTPException(status_code=404, detail="No se encontró esa dirección en el mapa")
    return found
