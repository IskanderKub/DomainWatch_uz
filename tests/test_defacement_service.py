# Unit tests for DefacementService / build_diff, using the in-memory snapshot fake.
from datetime import datetime, timedelta, timezone

from app.models.sql_models import CheckResult, Domain
from app.services.defacement_service import DefacementService, build_diff
from tests.fakes import FakeSnapshotRepository


def test_build_diff_marks_removed_and_added_words():
    segments = build_diff("hello world site", "hello hacked site")

    assert [(s.op, s.text) for s in segments] == [
        ("equal", "hello"),
        ("removed", "world"),
        ("added", "hacked"),
        ("equal", "site"),
    ]


def test_build_diff_trims_long_unchanged_runs():
    old = " ".join(f"w{i}" for i in range(100)) + " old"
    new = " ".join(f"w{i}" for i in range(100)) + " new"

    first = build_diff(old, new)[0]

    assert first.op == "equal"
    assert first.text.startswith("…")
    assert len(first.text.split()) < 20


def _add_snapshot(repo, domain_id, text, checked_at, check_id=None):
    repo.documents.append(
        {
            "_id": len(repo.documents),
            "domain_id": domain_id,
            "checked_at": checked_at,
            "last_seen_at": checked_at,
            "text_content": text,
            "check_id": check_id,
        }
    )


def test_list_for_domain_returns_only_suspected_checks_with_diff(db_session):
    domain = Domain(name="example.uz", url="https://example.uz")
    db_session.add(domain)
    db_session.commit()

    now = datetime.now(timezone.utc)
    ok_check = CheckResult(
        domain_id=domain.id, checked_at=now - timedelta(minutes=5),
        is_available=True, has_global_changes=False,
    )
    bad_check = CheckResult(
        domain_id=domain.id, checked_at=now, is_available=True,
        similarity_ratio=0.2, has_global_changes=True,
    )
    db_session.add_all([ok_check, bad_check])
    db_session.commit()

    repo = FakeSnapshotRepository()
    _add_snapshot(repo, domain.id, "welcome to site", now - timedelta(minutes=5), ok_check.id)
    _add_snapshot(repo, domain.id, "hacked by someone", now, bad_check.id)

    result = DefacementService(db_session, snapshot_repository=repo).list_for_domain(domain.id)

    assert len(result) == 1
    assert result[0].check_id == bad_check.id
    assert result[0].similarity_ratio == 0.2
    ops = {s.op for s in result[0].diff}
    assert ops == {"removed", "added"}


def test_list_for_domain_without_snapshots_returns_null_diff(db_session):
    domain = Domain(name="example.uz", url="https://example.uz")
    db_session.add(domain)
    db_session.commit()
    db_session.add(
        CheckResult(domain_id=domain.id, is_available=True, has_global_changes=True)
    )
    db_session.commit()

    result = DefacementService(
        db_session, snapshot_repository=FakeSnapshotRepository()
    ).list_for_domain(domain.id)

    assert len(result) == 1
    assert result[0].diff is None
