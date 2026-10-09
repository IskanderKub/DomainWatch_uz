# Pydantic schemas for domain-related API requests/responses.
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DomainCreate(BaseModel):
    """Payload for registering a new domain to monitor."""

    name: str
    url: str


class DomainRead(BaseModel):
    """Domain as returned by the API."""

    id: int
    name: str
    url: str
    is_active: bool
    created_at: datetime

    # from_attributes lets this schema be built directly from a SQLAlchemy Domain instance
    model_config = ConfigDict(from_attributes=True)


class DomainStats(BaseModel):
    """Aggregated statistics for one domain, computed with pandas (see StatsService)."""

    domain_id: int
    total_checks: int
    uptime_percent: float
    avg_response_time_ms: float | None
    last_check_at: datetime | None
    global_changes: int
