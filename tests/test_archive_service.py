# Unit tests for ArchiveImportService: the Wayback Machine is mocked (requests.get),
# MongoDB is replaced by the in-memory fake.
from datetime import datetime, timedelta, timezone

import pytest
import requests

from app.models.sql_models import CheckResult, Domain
from app.services.archive_service import ArchiveImportService, ArchiveUnavailableError
from app.services.defacement_service import DefacementService
from app.services.stats_service import StatsService
from tests.fakes import FakeSnapshotRepository


class FakeResponse:
    def __init__(self, json_data=None, text="", status_code=200):
        self._json = json_data
        self.text = text
        self.content = text.encode()
        self.status_code = status_code
        self.headers = {"Content-Type": "text/html; charset=utf-8"}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}")


def _ts(days_ago: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days_ago)).strftime("%Y%m%d%H%M%S")


def _make_domain(db_session) -> Domain:
    domain = Domain(name="example.uz", url="https://example.uz/")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)
    return domain


def _mock_archive(mocker, rows, pages):
    """rows: CDX [timestamp, status, digest] rows; pages: timestamp -> page html."""

    def fake_get(url, **kwargs):
        if "/cdx/" in url:
            return FakeResponse(json_data=[["timestamp", "statuscode", "digest"], *rows])
        timestamp = url.split("/web/")[1].split("id_")[0]
        return FakeResponse(text=pages[timestamp])

    mocker.patch("app.services.archive_service.time.sleep")
    return mocker.patch("app.services.archive_service.requests.get", side_effect=fake_get)


def test_import_records_availability_and_detects_changes(db_session, mocker):
    domain = _make_domain(db_session)
    old, ok, defaced, down, revisit = _ts(200), _ts(10), _ts(5), _ts(4), _ts(3)
    rows = [
        [old, "200", "A"],  # older than the snapshot TTL: availability only
        [ok, "200", "B"],
        [defaced, "200", "C"],
        [down, "503", "D"],
        [revisit, "-", "C"],
    ]
    pages = {
        ok: "<html><body>Ministry of Finance of Uzbekistan</body></html>",
        defaced: "<html><body>HACKED BY ANONYMOUS</body></html>",
    }
    get = _mock_archive(mocker, rows, pages)
    snapshots = FakeSnapshotRepository()

    imported = ArchiveImportService(db_session, snapshot_repository=snapshots).import_history(
        domain
    )

    assert imported == 5
    checks = db_session.query(CheckResult).order_by(CheckResult.checked_at).all()
    assert [c.source for c in checks] == ["archive"] * 5
    assert [c.is_available for c in checks] == [True, True, True, False, True]
    assert [c.status_code for c in checks] == [200, 200, 200, 503, None]
    assert checks[2].has_global_changes is True
    # one CDX query + the two page versions inside the TTL window
    assert get.call_count == 3

    defacements = DefacementService(db_session, snapshot_repository=snapshots).list_for_domain(
        domain.id
    )
    assert [d.check_id for d in defacements] == [checks[2].id]
    assert defacements[0].source == "archive"
    assert defacements[0].diff is not None


def test_import_skips_captures_after_monitoring_started(db_session, mocker):
    domain = _make_domain(db_session)
    db_session.add(
        CheckResult(
            domain_id=domain.id,
            checked_at=datetime.now(timezone.utc) - timedelta(days=2),
            is_available=True,
            status_code=200,
        )
    )
    db_session.commit()
    before, after = _ts(3), _ts(1)
    _mock_archive(mocker, [[before, "200", "A"], [after, "200", "B"]], {before: "x", after: "y"})

    imported = ArchiveImportService(
        db_session, snapshot_repository=FakeSnapshotRepository()
    ).import_history(domain)

    assert imported == 1


def test_reimport_replaces_previous_archive_history(db_session, mocker):
    domain = _make_domain(db_session)
    ts = _ts(3)
    _mock_archive(mocker, [[ts, "200", "A"]], {ts: "<p>hello</p>"})
    snapshots = FakeSnapshotRepository()
    service = ArchiveImportService(db_session, snapshot_repository=snapshots)

    service.import_history(domain)
    service.import_history(domain)

    assert db_session.query(CheckResult).count() == 1
    assert len(snapshots.documents) == 1


def test_archive_failure_keeps_existing_history(db_session, mocker):
    domain = _make_domain(db_session)
    ts = _ts(3)
    _mock_archive(mocker, [[ts, "200", "A"]], {ts: "<p>hello</p>"})
    service = ArchiveImportService(db_session, snapshot_repository=FakeSnapshotRepository())
    service.import_history(domain)

    mocker.patch(
        "app.services.archive_service.requests.get",
        side_effect=requests.ConnectionError("archive down"),
    )
    with pytest.raises(ArchiveUnavailableError):
        service.import_history(domain)

    assert db_session.query(CheckResult).count() == 1


def test_stats_ignore_archive_checks_except_changes(db_session):
    domain = _make_domain(db_session)
    db_session.add_all(
        [
            CheckResult(domain_id=domain.id, is_available=False, source="archive"),
            CheckResult(
                domain_id=domain.id,
                is_available=True,
                has_global_changes=True,
                source="archive",
            ),
            CheckResult(domain_id=domain.id, is_available=True, response_time_ms=50.0),
        ]
    )
    db_session.commit()

    stats = StatsService(db_session).get_domain_stats(domain.id)

    assert stats.total_checks == 1
    assert stats.uptime_percent == 100.0
    assert stats.global_changes == 1
