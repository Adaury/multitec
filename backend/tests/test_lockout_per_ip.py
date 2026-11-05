from app.core import lockout


def test_an_attacker_cannot_lock_the_owner_out_from_another_ip():
    for _ in range(lockout.MAX_FREE_ATTEMPTS):
        lockout.register_failure("admin@multitec.com", "203.0.113.7")
    assert lockout.seconds_locked("admin@multitec.com", "203.0.113.7") > 0  # el atacante queda bloqueado
    assert lockout.seconds_locked("admin@multitec.com", "190.167.1.20") == 0  # el dueño entra desde su conexión
    assert lockout.seconds_locked("ADMIN@multitec.com ", "203.0.113.7") > 0  # mayúsculas y espacios no lo esquivan


def test_guessing_from_many_ips_still_locks_the_whole_account():
    for i in range(lockout.MAX_ACCOUNT_ATTEMPTS):
        assert lockout.seconds_locked("oficina@multitec.com", f"10.0.0.{i}") == 0
        lockout.register_failure("oficina@multitec.com", f"10.0.0.{i}")
    assert lockout.seconds_locked("oficina@multitec.com", "10.0.9.9") > 0


def test_success_clears_both_counters():
    for _ in range(4):
        lockout.register_failure("tec@multitec.com", "1.1.1.1")
    lockout.register_success("tec@multitec.com", "1.1.1.1")
    lockout.register_failure("tec@multitec.com", "1.1.1.1")
    assert lockout.seconds_locked("tec@multitec.com", "1.1.1.1") == 0


def test_deeply_nested_json_is_a_bad_request_not_a_server_error(client, admin_token):
    from tests.conftest import auth_headers

    body = "[" * 5000 + "]" * 5000
    resp = client.post("/api/clients", content=body, headers={**auth_headers(admin_token), "Content-Type": "application/json"})
    assert resp.status_code == 400
