import logging


def test_browser_errors_are_logged_without_auth_and_cannot_forge_log_lines(client, caplog):
    with caplog.at_level(logging.WARNING, logger="multitec.client"):
        resp = client.post(
            "/api/client-errors",
            json={
                "kind": "error",
                "message": "x is not a function\nINFO fake line injected",
                "detail": "app.js:10:5 TypeError",
                "url": "/login",
            },
            headers={"User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0) Version/26.5\nforged"},
        )
    assert resp.status_code == 204
    lines = [r.getMessage() for r in caplog.records if r.name == "multitec.client"]
    assert len(lines) == 1
    line = lines[0]
    assert "x is not a function" in line and "iPhone" in line and "/login" in line
    assert "\n" not in line  # el texto enviado no pudo partir el registro en líneas falsas


def test_oversized_reports_are_rejected_and_the_endpoint_is_rate_limited(client):
    too_big = client.post("/api/client-errors", json={"message": "x" * 600})
    assert too_big.status_code == 422
    statuses = [client.post("/api/client-errors", json={"message": f"e{i}"}).status_code for i in range(25)]
    assert statuses.count(204) <= 20 and 429 in statuses
