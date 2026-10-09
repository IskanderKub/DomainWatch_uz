# Aggregated per-domain statistics (uptime%, average response time, ...), computed
# with pandas over the check history pulled from PostgreSQL.
import pandas as pd
from sqlalchemy.orm import Session

from app.repositories.check_repository import CheckRepository
from app.schemas.domain import DomainStats


class StatsService:
    def __init__(self, db: Session, check_repository: CheckRepository | None = None):
        self.check_repository = check_repository or CheckRepository(db)

    def get_domain_stats(self, domain_id: int, limit: int = 1000) -> DomainStats:
        checks = self.check_repository.list_for_domain(domain_id, limit=limit)

        if not checks:
            # domain has never been checked yet - return zeroed-out stats instead of
            # dividing by zero further down
            return DomainStats(
                domain_id=domain_id,
                total_checks=0,
                uptime_percent=0.0,
                avg_response_time_ms=None,
                last_check_at=None,
                global_changes=0,
            )

        # load check rows into a DataFrame so pandas can do the aggregation
        df = pd.DataFrame(
            [
                {
                    "is_available": c.is_available,
                    "response_time_ms": c.response_time_ms,
                    "has_global_changes": c.has_global_changes,
                    "checked_at": c.checked_at,
                }
                for c in checks
            ]
        )

        # mean of a boolean column == fraction of True values
        uptime_percent = float(df["is_available"].mean() * 100)

        # failed checks have response_time_ms == None, drop them before averaging
        avg_response_time_ms = df["response_time_ms"].dropna()
        avg_response_time_ms = (
            float(avg_response_time_ms.mean()) if not avg_response_time_ms.empty else None
        )

        return DomainStats(
            domain_id=domain_id,
            total_checks=len(df),
            uptime_percent=round(uptime_percent, 2),
            avg_response_time_ms=(
                round(avg_response_time_ms, 2) if avg_response_time_ms is not None else None
            ),
            last_check_at=df["checked_at"].max(),
            global_changes=int(df["has_global_changes"].sum()),
        )
