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
