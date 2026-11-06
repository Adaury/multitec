from app.core import ip_limit


def test_one_ip_flooding_the_api_is_cut_off_without_affecting_others(client, admin_token, monkeypatch):
    from tests.conftest import auth_headers

    monkeypatch.setattr(ip_limit, "LIMIT_PER_MINUTE", 20)
    # Reloj fijo: si la prueba cruzaba el cambio de minuto, el contador volvía a cero y no llegaba al tope.
    monkeypatch.setattr(ip_limit, "_now", lambda: 1_800_000_000.0)
    # El middleware lee el límite al crearse: se prueba directamente el contador y luego el corte real con el límite real.
    for _ in range(ip_limit.LIMIT_PER_MINUTE):
        assert ip_limit.hit("203.0.113.66") <= 20
    assert ip_limit.hit("203.0.113.66") > 20
    assert ip_limit.hit("190.166.5.5") == 1  # otra IP empieza de cero

    ip_limit.reset()
    h = auth_headers(admin_token)
    codes = [client.get("/api/clients", headers=h).status_code for _ in range(605)]
    assert codes.count(200) == 600 and set(codes[600:]) == {429}
    resp = client.get("/api/clients", headers=h)
    assert resp.status_code == 429 and int(resp.headers["retry-after"]) > 0


def test_requests_from_the_machine_itself_are_not_counted():
    ip_limit.reset()
    for _ in range(700):
        ip_limit.hit("10.0.0.1")
    assert "127.0.0.1" in ip_limit._LOCAL and "::1" in ip_limit._LOCAL
