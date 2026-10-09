# Integration tests for the /api/v1/domains/{id}/checks endpoints.
# CheckerService.check_domain itself is unit-tested separately (test_checker_service.py),
# so here it's mocked out - these tests only verify the HTTP wiring (status codes, 404s).
from datetime import datetime, timezone

from app.models.sql_models import CheckResult
from app.repositories.check_repository import CheckRepository
from app.repositories.domain_repository import DomainRepository
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
        has_global_changes=False,
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


def test_get_check_snapshot(client, db_session, monkeypatch):
    # 1. Создаем домен и проверку в тестовой БД (SQLite in-memory)
    domain = DomainRepository(db_session).create("example.uz", "https://example.uz")
    check = CheckRepository(db_session).create(
        CheckResult(
            domain_id=domain.id,
            is_available=True,
            status_code=200,
            response_time_ms=150.0,
        )
    )

    # 2. Мокаем SnapshotRepository, чтобы не задействовать реальный MongoDB
    fake_snapshot = {
        "check_id": check.id,
        "domain_id": domain.id,
        "text_content": "Hello World",
        "checked_at": "2026-03-30T10:00:00Z",
        "last_seen_at": "2026-03-30T10:00:00Z",
    }

    from app.repositories.snapshot_repository import SnapshotRepository

    monkeypatch.setattr(
        SnapshotRepository, "get_by_check_id", lambda self, check_id: fake_snapshot
    )

    # 3. Выполняем GET-запрос (с учетом префикса /api/v1)
    response = client.get(f"/api/v1/domains/{domain.id}/checks/{check.id}/snapshot")

    assert response.status_code == 200
    data = response.json()
    assert data["check_id"] == check.id
    assert data["text_content"] == "Hello World"
