# Data-access layer for CheckResult rows in PostgreSQL.
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

    def list_for_domain(self, domain_id: int, limit: int = 100) -> list[CheckResult]:
        # most recent checks first
        return (
            self.db.query(CheckResult)
            .filter(CheckResult.domain_id == domain_id)
            .order_by(CheckResult.checked_at.desc())
            .limit(limit)
            .all()
        )

    def get_latest_for_domain(self, domain_id: int) -> CheckResult | None:
        return (
            self.db.query(CheckResult)
            .filter(CheckResult.domain_id == domain_id)
            .order_by(CheckResult.checked_at.desc())
            .first()
        )

    def get_by_id(self, check_id: int) -> CheckResult | None:
        return self.db.get(CheckResult, check_id)
