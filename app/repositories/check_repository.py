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

    def list_for_domain(
        self,
        domain_id: int,
        limit: int = 100,
        since: datetime | None = None,
        until: datetime | None = None,
        is_available: bool | None = None,
    ) -> list[CheckResult]:
        # most recent checks first; since/until narrow it to a time window [since, until)
        query = self.db.query(CheckResult).filter(CheckResult.domain_id == domain_id)
        if is_available is not None:
            query = query.filter(CheckResult.is_available.is_(is_available))
        if since is not None:
            query = query.filter(CheckResult.checked_at >= since)
        if until is not None:
            query = query.filter(CheckResult.checked_at < until)
        return query.order_by(CheckResult.checked_at.desc()).limit(limit).all()

    def get_latest_for_domain(self, domain_id: int) -> CheckResult | None:
        return (
            self.db.query(CheckResult)
            .filter(CheckResult.domain_id == domain_id)
            .order_by(CheckResult.checked_at.desc())
            .first()
        )
