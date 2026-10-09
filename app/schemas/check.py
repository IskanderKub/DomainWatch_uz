# Pydantic schemas for check-result and snapshot API responses.
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field


class CheckResultRead(BaseModel):
    """A single check result as returned by the API."""

    id: int
    domain_id: int
    checked_at: datetime
    is_available: bool
    status_code: int | None
    response_time_ms: float | None
    similarity_ratio: float | None
    has_global_changes: bool
    error_message: str | None
    source: str  # "live" | "archive" (imported from the Wayback Machine)

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def change_percent(self) -> float | None:
        """How much of the page text changed, as a percentage.

        The inverse of similarity_ratio, exposed so clients can show "changed by
        73%" instead of a bare flag. None when there was nothing to compare against.
        """
        if self.similarity_ratio is None:
            return None
        return round((1 - self.similarity_ratio) * 100, 1)


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
    """A check flagged with has_global_changes, together with what changed on the page."""

    check_id: int
    checked_at: datetime
    similarity_ratio: float | None
    source: str  # "live" | "archive"
    # None when the snapshots needed for the diff are gone (TTL) or Mongo is unreachable
    diff: list[DiffSegment] | None
