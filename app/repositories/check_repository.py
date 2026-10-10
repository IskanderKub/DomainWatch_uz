# Data-access layer for CheckResult rows in PostgreSQL.
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.sql_models import CheckResult


class CheckRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, check: CheckResult) -> CheckResult:
        self.db.add(check)
        self.db.commit()
        self.db.refresh(check)
        return check

    def create_many(self, checks: list[CheckResult]) -> None:
        self.db.add_all(checks)
        self.db.commit()

    def delete_archived_for_domain(self, domain_id: int) -> None:
        # not committed on its own: the archive import commits the deletion together
        # with the replacement rows, so a failed import keeps the previous history
        self.db.query(CheckResult).filter(
            CheckResult.domain_id == domain_id, CheckResult.source == "archive"
        ).delete(synchronize_session=False)

    def list_for_domain(
        self,
        domain_id: int,
        limit: int = 100,
        since: datetime | None = None,
        until: datetime | None = None,
        is_available: bool | None = None,
        source: str | None = None,
    ) -> list[CheckResult]:
        # most recent checks first; since/until narrow it to a time window [since, until).
        # id breaks ties: checked_at defaults to the insert moment, so several checks
        # can share one timestamp and the order between them would otherwise be
        # undefined - which decides is_available_now in StatsService.
        query = self.db.query(CheckResult).filter(CheckResult.domain_id == domain_id)
        if source is not None:
            query = query.filter(CheckResult.source == source)
        if is_available is not None:
            query = query.filter(CheckResult.is_available.is_(is_available))
        if since is not None:
            query = query.filter(CheckResult.checked_at >= since)
        if until is not None:
            query = query.filter(CheckResult.checked_at < until)
        return (
            query.order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
            .limit(limit)
            .all()
        )

    def get_latest_for_domain(self, domain_id: int) -> CheckResult | None:
        return (
            self.db.query(CheckResult)
            .filter(CheckResult.domain_id == domain_id)
            .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
            .first()
        )

    def get_earliest_live_for_domain(self, domain_id: int) -> CheckResult | None:
        return (
            self.db.query(CheckResult)
            .filter(CheckResult.domain_id == domain_id, CheckResult.source == "live")
            .order_by(CheckResult.checked_at.asc(), CheckResult.id.asc())
            .first()
        )

    def count_global_changes(self, domain_id: int) -> int:
        return (
            self.db.query(CheckResult)
            .filter(
                CheckResult.domain_id == domain_id,
                CheckResult.has_global_changes.is_(True),
            )
            .count()
        )

    def get_by_id(self, check_id: int) -> CheckResult | None:
        return self.db.get(CheckResult, check_id)
