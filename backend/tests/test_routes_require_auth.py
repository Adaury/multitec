"""Toda ruta de la API pide sesión, salvo las públicas a propósito. Si se agrega una ruta nueva sin protección, esta
prueba falla y obliga a decidir: protegerla o agregarla aquí a la lista de públicas (con su motivo)."""

from app.main import app

# Rutas públicas a propósito (no necesitan sesión).
PUBLIC = {
    ("GET", "/api/health"),  # chequeo de estado
    ("POST", "/api/auth/login"),
    ("POST", "/api/auth/refresh"),  # usa la cookie del refresh token
    ("POST", "/api/auth/logout"),
    ("POST", "/api/client-errors"),  # la app reporta errores aunque la sesión haya caído
    ("GET", "/api/site"),  # página pública: planes y testimonios publicados
    ("GET", "/api/signup/info"),
    ("POST", "/api/signup"),  # registro de empresas
    ("POST", "/api/site/experiences"),  # un cliente cuenta su experiencia (llega sin publicar)
}
PUBLIC_PREFIXES = ("/api/public/", "/api/portal/")  # portal del cliente: entra con un enlace secreto


def _routes(routes):
    for r in routes:
        inner = getattr(r, "routes", None) or getattr(getattr(r, "original_router", None), "routes", None)
        if inner and not hasattr(r, "endpoint"):
            yield from _routes(inner)
        else:
            yield r


def test_every_private_route_rejects_requests_without_a_session(client):
    exposed, checked = [], 0
    for route in _routes(app.routes):
        path = getattr(route, "path", "")
        if not path.startswith("/api") or path.startswith(PUBLIC_PREFIXES):
            continue
        for method in sorted(getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}):
            if (method, path) in PUBLIC:
                continue
            url = path
            for part in [p for p in path.split("/") if p.startswith("{")]:
                url = url.replace(part, "1")
            checked += 1
            status = client.request(method, url).status_code
            if status not in (401, 403):
                exposed.append(f"{method} {path} -> {status}")
    assert checked > 200
    assert exposed == [], "Rutas que responden sin sesión: " + "; ".join(exposed)
