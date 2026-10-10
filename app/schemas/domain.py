# Pydantic schemas for domain-related API requests/responses.
from datetime import datetime
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DomainCreate(BaseModel):
    """Payload for registering a new domain to monitor."""

    # the name is the natural key (it's what 409 Conflict is raised on) and the label
    # the dashboard renders, so it can be neither empty nor arbitrarily long
    name: str = Field(min_length=1, max_length=255)
    url: str

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, name: str) -> str:
        # "   " passes min_length but is not a usable name
        name = name.strip()
        if not name:
            raise ValueError("Name must not be empty")
        return name

    @field_validator("url")
    @classmethod
    def url_must_be_http(cls, url: str) -> str:
        # without this, "example.uz" is stored as-is and every check fails with
        # "No scheme supplied", which looks like the site being down
        url = url.strip()
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError(
                "URL must start with http:// or https://, e.g. https://example.uz"
            )
        return url


class DomainUpdate(BaseModel):
    """Payload for pausing or resuming monitoring of a domain."""

    is_active: bool


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
    # result of the most recent check, so the UI can show the current state
    # rather than one derived from the whole history's uptime
    is_available_now: bool | None
    global_changes: int