"""Health, error mapping for failures the rules cannot cause, logging and the test clock."""

import logging

import pytest
from sqlalchemy.exc import DataError, IntegrityError, OperationalError

from app.services import master_data


def test_health_checks_the_database(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok" and body["database"] == "ok"


def test_openapi_documents_the_api(client):
    spec = client.get("/openapi.json").json()
    assert "/api/v1/deliveries/preview" in spec["paths"]
    assert "/api/v1/payouts/{payout_id}/finalise" in spec["paths"]
    assert client.get("/docs").status_code == 200


@pytest.mark.parametrize(
    ("error", "status", "code"),
    [
        (IntegrityError("stmt", {}, Exception("duplicate key")), 409, "conflict"),
        (DataError("stmt", {}, Exception("numeric overflow")), 422, "value_out_of_range"),
        (
            OperationalError("stmt", {}, Exception("connection refused")),
            503,
            "database_unavailable",
        ),
        (RuntimeError("secret internal detail: password=hunter2"), 500, "internal_error"),
    ],
)
def test_infrastructure_failures_map_to_safe_responses(client, monkeypatch, error, status, code):
    def explode(*args, **kwargs):
        raise error

    monkeypatch.setattr(master_data, "list_farmers", explode)
    response = client.get("/api/v1/farmers")
    assert response.status_code == status
    body = response.json()["error"]
    assert body["code"] == code
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert "hunter2" not in response.text and "Traceback" not in response.text
    assert "duplicate key" not in response.text and "refused" not in response.text


def test_unexpected_error_is_logged_with_stack_trace_and_request_id(client, monkeypatch, caplog):
    monkeypatch.setattr(master_data, "list_farmers", lambda *a, **k: 1 / 0)
    with caplog.at_level(logging.ERROR):
        response = client.get("/api/v1/farmers", headers={"X-Request-ID": "trace-500"})
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == "trace-500"
    record = next(r for r in caplog.records if r.getMessage() == "unhandled_exception")
    assert record.levelno == logging.ERROR and record.exc_info


def test_rule_violation_is_logged_as_warning_with_context(api, world, caplog):
    with caplog.at_level(logging.INFO):
        api.client.post(
            "/api/v1/deliveries",
            json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], moisture="30"),
        )
    warning = next(r for r in caplog.records if r.getMessage() == "domain_error")
    assert warning.levelno == logging.WARNING
    assert warning.code == "moisture_above_maximum"
    assert warning.path == "/api/v1/deliveries"


def test_request_log_has_method_path_status_and_no_body(api, world, caplog):
    with caplog.at_level(logging.INFO):
        api.delivery(world["farmer"]["id"], world["crop"]["id"])
    request_logs = [r for r in caplog.records if r.getMessage() == "request"]
    last = request_logs[-1]
    assert (last.method, last.path, last.status) == ("POST", "/api/v1/deliveries", 201)
    assert last.duration_ms >= 0
    assert not hasattr(last, "body")
    created = next(r for r in caplog.records if r.getMessage() == "delivery_created")
    assert created.farmer_id == world["farmer"]["id"] and created.delivery_id


def test_invalid_test_clock_is_rejected_with_a_clear_message(client):
    response = client.get("/api/v1/farmers/1/ledger", headers={"X-Test-Clock": "yesterday"})
    # the clock dependency is only evaluated on routes that use it
    response = client.post(
        "/api/v1/farmers/1/advances",
        json={"amount": "10", "given_on": "2026-10-01"},
        headers={"X-Test-Clock": "yesterday"},
    )
    assert response.status_code == 422
    assert "X-Test-Clock" in response.json()["error"]["message"]


def test_test_clock_accepts_date_and_datetime_forms(api, world):
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-25")
    for clock in ("2026-10-25", "2026-10-25T10:00:00+05:30", "2026-10-25T10:00:00"):
        response = api.client.post(
            "/api/v1/deliveries/preview", json=body, headers={"X-Test-Clock": clock}
        )
        assert response.status_code == 200, clock


def test_test_clock_uses_ist_not_utc_for_today(api, world):
    # 19:00 UTC on 24 Oct is already 00:30 IST on 25 Oct, so a delivery dated 25 Oct is valid.
    body = api.delivery_body(world["farmer"]["id"], world["crop"]["id"], delivered_on="2026-10-25")
    response = api.client.post(
        "/api/v1/deliveries/preview",
        json=body,
        headers={"X-Test-Clock": "2026-10-24T19:00:00+00:00"},
    )
    assert response.status_code == 200


def test_cors_allows_the_configured_ui_origin(client):
    allowed = client.options(
        "/api/v1/farmers",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"
    other = client.options(
        "/api/v1/farmers",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "POST"},
    )
    assert "access-control-allow-origin" not in other.headers


def test_rule_violation_log_carries_the_domain_identifiers(api, world, caplog):
    with caplog.at_level(logging.INFO):
        api.client.post(
            "/api/v1/deliveries",
            json=api.delivery_body(world["farmer"]["id"], world["crop"]["id"], moisture="30"),
        )
    warning = next(r for r in caplog.records if r.getMessage() == "domain_error")
    assert warning.context["farmer_id"] == world["farmer"]["id"]
    assert warning.context["crop_id"] == world["crop"]["id"]
