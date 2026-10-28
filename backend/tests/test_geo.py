from unittest.mock import MagicMock, patch

from app.api.routers import geo
from tests.conftest import auth_headers


def _response(payload):
    resp = MagicMock()
    resp.json.return_value = payload
    resp.raise_for_status.return_value = None
    return resp


def test_search_requires_login(client):
    assert client.get("/api/geo/search", params={"q": "Av. Principal 120, Santo Domingo"}).status_code == 401


def test_search_returns_coordinates_and_caches(client, admin_token):
    geo.reset_cache()
    payload = [{"lat": "18.4861", "lon": "-69.9312", "display_name": "Santo Domingo"}]
    with patch("app.api.routers.geo.httpx.get", return_value=_response(payload)) as mocked, patch(
        "app.api.routers.geo.time.sleep"
    ):
        first = client.get("/api/geo/search", params={"q": "Av. Principal 120, Santo Domingo"}, headers=auth_headers(admin_token))
        again = client.get("/api/geo/search", params={"q": "av. principal 120,  santo domingo"}, headers=auth_headers(admin_token))
    assert first.status_code == 200 and first.json()["lat"] == 18.4861 and first.json()["lng"] == -69.9312
    assert again.json() == first.json()
    assert mocked.call_count == 1  # la segunda salió del caché


def test_search_not_found_and_provider_down(client, admin_token):
    geo.reset_cache()
    h = auth_headers(admin_token)
    with patch("app.api.routers.geo.httpx.get", return_value=_response([])), patch("app.api.routers.geo.time.sleep"):
        assert client.get("/api/geo/search", params={"q": "calle que no existe 999"}, headers=h).status_code == 404
    geo.reset_cache()
    import httpx

    with patch("app.api.routers.geo.httpx.get", side_effect=httpx.ConnectError("sin red")), patch(
        "app.api.routers.geo.time.sleep"
    ):
        down = client.get("/api/geo/search", params={"q": "otra calle 123 santiago"}, headers=h)
    assert down.status_code == 503 and "Cómo llegar" in down.json()["detail"]


def test_search_is_limited_to_the_configured_countries_and_never_falls_back_worldwide(client, admin_token):
    geo.reset_cache()
    seen = []

    def fake_get(url, params=None, **kwargs):
        seen.append(dict(params))
        return _response([])

    with patch("app.api.routers.geo.httpx.get", side_effect=fake_get), patch("app.api.routers.geo.time.sleep"):
        resp = client.get("/api/geo/search", params={"q": "calle duarte 45 inventada"}, headers=auth_headers(admin_token))
    assert resp.status_code == 404
    assert len(seen) == 1 and seen[0]["countrycodes"] == "do"  # una sola consulta, acotada a República Dominicana
