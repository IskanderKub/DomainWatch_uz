# SQLAlchemy ORM models for the structured data stored in PostgreSQL.
# Raw page-text snapshots live in MongoDB instead (see app/repositories/snapshot_repository.py).
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.core.postgres import Base


def utcnow() -> datetime:
    # used as a Column default so every row gets a timezone-aware UTC timestamp
    return datetime.now(timezone.utc)


class Domain(Base):
    """A domain being monitored, e.g. example.uz."""

    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)  # e.g. example.uz
    url = Column(String, nullable=False)  # e.g. https://example.uz
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)

    # one-to-many: deleting a domain also deletes its check history
    checks = relationship(
        "CheckResult", back_populates="domain", cascade="all, delete-orphan"
    )


class CheckResult(Base):
    """A single availability/content check performed against a Domain."""

    __tablename__ = "check_results"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id"), nullable=False, index=True)
    checked_at = Column(DateTime(timezone=True), default=utcnow, nullable=False, index=True)

    is_available = Column(Boolean, nullable=False)
    status_code = Column(Integer, nullable=True)
    response_time_ms = Column(Float, nullable=True)

    # similarity_ratio: text similarity (0..1) vs the previous snapshot, from difflib.
    # None on the very first check for a domain, since there's nothing to compare against.
    similarity_ratio = Column(Float, nullable=True)
    # True when more than CONTENT_CHANGE_THRESHOLD of the page text changed at once.
    # Deliberately not called "defacement": the metric measures how much changed, not
    # whether the change was malicious - a redesign trips it, a one-line injection does not.
    has_global_changes = Column(Boolean, default=False, nullable=False)

    error_message = Column(String, nullable=True)  # set when the request itself failed

    domain = relationship("Domain", back_populates="checks")
