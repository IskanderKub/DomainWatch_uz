# Integration tests for the /api/v1/domains/{id}/checks endpoints.
# CheckerService.check_domain itself is unit-tested separately (test_checker_service.py),
# so here it's mocked out - these tests only verify the HTTP wiring (status codes, 404s).
from datetime import datetime, timezone

from app.models.sql_models import CheckResult
from app.services.checker_service import CheckerService


def test_trigger_check_missing_domain_returns_404(client):
    response = client.post("/api/v1/domains/999/checks")
    assert response.status_code == 404


def test_trigger_check_returns_result(client, mocker):
    created = client.post(
        "/api/v1/domains", json={"name": "example.uz", "url": "https://example.uz"}
    ).json()

    # a plain (unsaved) CheckResult is enough - the response only needs its attributes
    fake_result = CheckResult(
        id=1,
        domain_id=created["id"],
        checked_at=datetime.now(timezone.utc),
        is_available=True,
        status_code=200,
        response_time_ms=123.4,
        similarity_ratio=0.99,
        is_suspected_defacement=False,
    )
    mocker.patch.object(CheckerService, "check_domain", return_value=fake_result)

    response = client.post(f"/api/v1/domains/{created['id']}/checks")

    assert response.status_code == 201
    body = response.json()
    assert body["is_available"] is True
    assert body["status_code"] == 200


def test_list_checks_for_missing_domain_returns_404(client):
    response = client.get("/api/v1/domains/999/checks")
    assert response.status_code == 404


def test_list_defacements_for_missing_domain_returns_404(client):
    response = client.get("/api/v1/domains/999/defacements")
    assert response.status_code == 404


def test_list_checks_filters_by_time_window(client, db_session):
    created = client.post(
        "/api/v1/domains", json={"name": "example.uz", "url": "https://example.uz"}
    ).json()
    for day in (1, 2, 3):
        db_session.add(
            CheckResult(
                domain_id=created["id"],
                checked_at=datetime(2026, 10, day, 12, tzinfo=timezone.utc),
                is_available=True,
                is_suspected_defacement=False,
            )
        )
    db_session.commit()

    response = client.get(
        f"/api/v1/domains/{created['id']}/checks",
        params={"since": "2026-10-02T00:00:00Z", "until": "2026-10-03T00:00:00Z"},
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["checked_at"].startswith("2026-10-02")


def test_list_checks_filters_by_availability(client, db_session):
    created = client.post(
        "/api/v1/domains", json={"name": "example.uz", "url": "https://example.uz"}
    ).json()
    db_session.add_all(
        [
            CheckResult(domain_id=created["id"], is_available=True, status_code=200),
            CheckResult(
                domain_id=created["id"],
                is_available=False,
                status_code=None,
                error_message="timeout",
            ),
        ]
    )
    db_session.commit()

    response = client.get(
        f"/api/v1/domains/{created['id']}/checks", params={"is_available": "false"}
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["error_message"] == "timeout"
