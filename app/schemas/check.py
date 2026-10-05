# Pydantic schemas for check-result and snapshot API responses.
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CheckResultRead(BaseModel):
    """A single check result as returned by the API."""

    id: int
    domain_id: int
    checked_at: datetime
    is_available: bool
    status_code: int | None
    response_time_ms: float | None
    similarity_ratio: float | None
    is_suspected_defacement: bool
    error_message: str | None

    model_config = ConfigDict(from_attributes=True)


class SnapshotRead(BaseModel):
    """A raw page-text snapshot, as stored in MongoDB."""

    domain_id: int
    checked_at: datetime
    text_content: str


class DiffSegment(BaseModel):
    """A run of words that was kept, removed or added between two snapshots."""

    op: str  # "equal" | "removed" | "added"
    text: str


class DefacementRead(BaseModel):
    """A suspected-defacement check, together with what changed on the page."""

    check_id: int
    checked_at: datetime
    similarity_ratio: float | None
    # None when the snapshots needed for the diff are gone (TTL) or Mongo is unreachable
    diff: list[DiffSegment] | None
