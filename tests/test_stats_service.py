# Unit tests for StatsService's pandas-based aggregation.
from app.models.sql_models import CheckResult, Domain
from app.services.stats_service import StatsService


def _make_domain_with_checks(db_session) -> Domain:
    domain = Domain(name="example.uz", url="https://example.uz")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    # 2 available checks (100ms, 200ms) + 1 failed check (no response time) +
    # 1 of the available checks flagged with global changes
    checks = [
        CheckResult(
            domain_id=domain.id,
            is_available=True,
            status_code=200,
            response_time_ms=100.0,
            similarity_ratio=0.95,
            has_global_changes=False,
        ),
        CheckResult(
            domain_id=domain.id,
            is_available=True,
            status_code=200,
            response_time_ms=200.0,
            similarity_ratio=0.1,
            has_global_changes=True,
        ),
        CheckResult(
            domain_id=domain.id,
            is_available=False,
            status_code=None,
            response_time_ms=None,
            similarity_ratio=None,
            has_global_changes=False,
            error_message="timeout",
        ),
    ]
    db_session.add_all(checks)
    db_session.commit()
    return domain


def test_get_domain_stats(db_session):
    domain = _make_domain_with_checks(db_session)

    stats = StatsService(db_session).get_domain_stats(domain.id)

    assert stats.total_checks == 3
    assert round(stats.uptime_percent, 2) == round(2 / 3 * 100, 2)
    # average of 100.0 and 200.0; the failed check's None is excluded
    assert stats.avg_response_time_ms == 150.0
    assert stats.global_changes == 1
    # the most recent check (the timeout) decides the current state
    assert stats.is_available_now is False


def test_get_domain_stats_no_checks(db_session):
    domain = Domain(name="empty.uz", url="https://empty.uz")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    stats = StatsService(db_session).get_domain_stats(domain.id)

    assert stats.total_checks == 0
    assert stats.uptime_percent == 0.0
    assert stats.avg_response_time_ms is None
    assert stats.last_check_at is None


def test_is_available_now_is_deterministic_when_timestamps_collide(db_session):
    # checked_at defaults to the insert moment, so several checks of one domain can
    # share a timestamp. Without a tiebreaker the order between them is undefined and
    # is_available_now - taken from the first row - flips between runs. The timestamps
    # here are identical on purpose, to reproduce that collision every time.
    from datetime import datetime, timezone

    from app.models.sql_models import CheckResult, Domain

    domain = Domain(name="tie.uz", url="https://tie.uz")
    db_session.add(domain)
    db_session.commit()
    db_session.refresh(domain)

    same_moment = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    db_session.add_all(
        [
            CheckResult(domain_id=domain.id, checked_at=same_moment, is_available=True),
            CheckResult(domain_id=domain.id, checked_at=same_moment, is_available=True),
            # inserted last, so this is the current state
            CheckResult(
                domain_id=domain.id, checked_at=same_moment, is_available=False
            ),
        ]
    )
    db_session.commit()

    stats = StatsService(db_session).get_domain_stats(domain.id)

    assert stats.total_checks == 3
    assert stats.is_available_now is False
