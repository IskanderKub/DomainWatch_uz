# Unit tests for CheckerService: HTTP calls are mocked (mocker.patch on requests.get)
# and MongoDB is replaced by an in-memory fake, so no network/DB access happens.
import requests

from app.core.config import settings
from app.models.sql_models import Domain
from app.services.checker_service import CheckerService
from tests.fakes import FakeSnapshotRepository


class FakeResponse:
    """Minimal stand-in for requests.Response, only the attributes checker_service reads."""

    def __init__(self, status_code=200, text="", ok=True):
        self.status_code = status_code
        self.text = text
        self.ok = ok


def _make_domain(db_session) -> Domain:
    domain = Domain(name="example.uz", url="https://example.uz")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)
    return domain


def test_check_domain_first_check_has_no_similarity(db_session, mocker):
    # first-ever check for a domain: nothing to compare the snapshot against yet
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        return_value=FakeResponse(text="<html><body>Ministry of Finance</body></html>"),
    )
    snapshot_repo = FakeSnapshotRepository()
    service = CheckerService(db_session, snapshot_repository=snapshot_repo)

    result = service.check_domain(domain)

    assert result.is_available is True
    assert result.status_code == 200
    assert result.similarity_ratio is None
    assert result.is_suspected_defacement is False
    # HTML tags are stripped before saving the snapshot
    assert snapshot_repo.documents[0]["text_content"] == "Ministry of Finance"


def test_check_domain_flags_defacement_on_drastic_change(db_session, mocker):
    # simulates the classic defacement scenario from the spec: page content is
    # replaced wholesale, so similarity should fall well below the threshold
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        return_value=FakeResponse(text="<html><body>HACKED BY ANONYMOUS</body></html>"),
    )
    snapshot_repo = FakeSnapshotRepository()
    snapshot_repo.save(domain.id, "Ministry of Finance of Uzbekistan")
    service = CheckerService(db_session, snapshot_repository=snapshot_repo)

    result = service.check_domain(domain)

    assert result.similarity_ratio < settings.content_change_threshold
    assert result.is_suspected_defacement is True


def test_check_domain_no_defacement_on_minor_change(db_session, mocker):
    # a small edit to existing content should stay above the threshold and not
    # be flagged as a suspected defacement
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        return_value=FakeResponse(
            text="<html><body>Ministry of Finance, updated</body></html>"
        ),
    )
    snapshot_repo = FakeSnapshotRepository()
    snapshot_repo.save(domain.id, "Ministry of Finance")
    service = CheckerService(db_session, snapshot_repository=snapshot_repo)

    result = service.check_domain(domain)

    assert result.similarity_ratio >= settings.content_change_threshold
    assert result.is_suspected_defacement is False


def test_check_domain_handles_request_failure(db_session, mocker):
    # network-level failure (host down, DNS error, etc.) should be recorded as
    # unavailable rather than raising out of check_domain
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        side_effect=requests.ConnectionError("connection refused"),
    )
    service = CheckerService(db_session, snapshot_repository=FakeSnapshotRepository())

    result = service.check_domain(domain)

    assert result.is_available is False
    assert result.status_code is None
    assert result.error_message == "connection refused"


def test_check_domain_reuses_snapshot_when_content_unchanged(db_session, mocker):
    # unchanged content should not create a second snapshot document
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        return_value=FakeResponse(text="<html><body>Ministry of Finance</body></html>"),
    )
    snapshot_repo = FakeSnapshotRepository()
    service = CheckerService(db_session, snapshot_repository=snapshot_repo)

    service.check_domain(domain)
    service.check_domain(domain)

    assert len(snapshot_repo.documents) == 1
    assert snapshot_repo.documents[0]["seen_count"] == 2


def test_check_domain_skips_snapshot_on_error_status(db_session, mocker):
    # a blocked/failing response must not be stored as if it were site content
    domain = _make_domain(db_session)
    mocker.patch(
        "app.services.checker_service.requests.get",
        return_value=FakeResponse(
            status_code=403, ok=False, text="<html><body>Forbidden</body></html>"
        ),
    )
    snapshot_repo = FakeSnapshotRepository()
    service = CheckerService(db_session, snapshot_repository=snapshot_repo)

    result = service.check_domain(domain)

    assert result.is_available is False
    assert result.status_code == 403
    assert result.similarity_ratio is None
    assert snapshot_repo.documents == []
