# Imports a domain's history from before it was added to monitoring, using the
# Internet Archive (Wayback Machine): every capture becomes an "archive" CheckResult,
# and recent page versions are downloaded so content changes are detected as well.
import logging
import threading
import time
from datetime import datetime, timedelta, timezone

import requests
from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.postgres import SessionLocal
from app.models.sql_models import CheckResult, Domain
from app.repositories.check_repository import CheckRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.services.checker_service import _extract_text, _response_html, _similarity

logger = logging.getLogger(__name__)

CDX_URL = "https://web.archive.org/cdx/search/cdx"
# "id_" returns the page exactly as captured, without the Wayback toolbar/rewriting
RAW_CAPTURE_URL = "https://web.archive.org/web/{timestamp}id_/{url}"
ARCHIVE_TIMEOUT_SECONDS = 60  # the archive is much slower than a typical site
MAX_CAPTURES = 5000
FETCH_DELAY_SECONDS = 1  # the archive throttles clients that download too fast
# the capture index answers 503 under load (e.g. several imports at once) - retry
CDX_RETRY_DELAYS_SECONDS = (10, 30)

# one import at a time: parallel imports get rate-limited by the archive
_import_lock = threading.Lock()


class ArchiveUnavailableError(Exception):
    """Raised when the Wayback Machine capture index can't be queried."""


def _parse_timestamp(timestamp: str) -> datetime:
    return datetime.strptime(timestamp, "%Y%m%d%H%M%S").replace(tzinfo=timezone.utc)


def _as_utc(value: datetime) -> datetime:
    # SQLite (tests) hands back naive datetimes; Postgres returns aware ones
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


class ArchiveImportService:
    def __init__(
        self,
        db: Session,
        check_repository: CheckRepository | None = None,
        snapshot_repository: SnapshotRepository | None = None,
    ):
        self.check_repository = check_repository or CheckRepository(db)
        self.snapshot_repository = snapshot_repository or SnapshotRepository()

    def import_history(self, domain: Domain) -> int:
        """Replace the domain's archive history; returns the number of imported checks."""
        # import only what precedes our own monitoring - from then on live checks exist
        earliest_live = self.check_repository.get_earliest_live_for_domain(domain.id)
        now = datetime.now(timezone.utc)
        until = _as_utc(earliest_live.checked_at) if earliest_live else now
        since = until - timedelta(days=settings.archive_backfill_days)

        captures = [
            capture
            for capture in self._list_captures(domain.url, since)
            if capture["captured_at"] < until
        ]
        texts = self._fetch_page_versions(
            domain.url, captures, fetch_since=now - timedelta(days=settings.snapshot_ttl_days)
        )

        checks = []
        previous_text = None
        for capture in captures:
            check = CheckResult(
                domain_id=domain.id,
                checked_at=capture["captured_at"],
                is_available=capture["is_available"],
                status_code=capture["status_code"],
                source="archive",
            )
            text_content = texts.get(capture["timestamp"])
            if text_content is not None:
                if previous_text is not None:
                    check.similarity_ratio = _similarity(previous_text, text_content)
                    check.has_global_changes = (
                        check.similarity_ratio < settings.content_change_threshold
                    )
                previous_text = text_content
            checks.append(check)

        # a re-import replaces the previous one instead of duplicating it
        self.check_repository.delete_archived_for_domain(domain.id)
        self.check_repository.create_many(checks)
        self._store_snapshots(domain.id, captures, checks, texts)

        logger.info(
            "Imported %d archive captures for %s (%d page versions)",
            len(checks),
            domain.name,
            len(texts),
        )
        return len(checks)

    def _list_captures(self, url: str, since: datetime) -> list[dict]:
        for delay in (*CDX_RETRY_DELAYS_SECONDS, None):
            try:
                rows = self._query_captures(url, since)
                break
            except (requests.RequestException, ValueError) as exc:
                if delay is None:
                    raise ArchiveUnavailableError(f"Wayback Machine query failed: {exc}") from exc
                logger.warning("Wayback Machine query failed, retrying in %ss: %s", delay, exc)
                time.sleep(delay)
        return self._parse_captures(rows)

    def _query_captures(self, url: str, since: datetime) -> list[list[str]]:
        response = requests.get(
            CDX_URL,
            params={
                "url": url,
                "output": "json",
                "fl": "timestamp,statuscode,digest",
                "from": since.strftime("%Y%m%d%H%M%S"),
                "collapse": "timestamp:10",  # at most one capture per hour
                "limit": -MAX_CAPTURES,  # negative = the most recent ones
            },
            headers={"User-Agent": settings.user_agent},
            timeout=ARCHIVE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()

    def _parse_captures(self, rows: list[list[str]]) -> list[dict]:
        captures = []
        for timestamp, status, digest in rows[1:]:  # first row is the header
            # "-" marks a revisit: the crawler got content identical to an earlier capture
            status_code = int(status) if status.isdigit() else None
            captures.append(
                {
                    "timestamp": timestamp,
                    "captured_at": _parse_timestamp(timestamp),
                    "status_code": status_code,
                    "is_available": status_code is None or status_code < 400,
                    "digest": digest,
                }
            )
        return captures

    def _fetch_page_versions(
        self, url: str, captures: list[dict], fetch_since: datetime
    ) -> dict[str, str]:
        # only versions newer than the snapshot TTL are worth downloading - older
        # snapshots would be expired by Mongo right away, leaving nothing to diff
        candidates = []
        previous_digest = None
        for capture in captures:
            if capture["captured_at"] < fetch_since or capture["status_code"] is None:
                continue
            if not capture["is_available"] or capture["digest"] == previous_digest:
                continue
            previous_digest = capture["digest"]
            candidates.append(capture)
        candidates = candidates[-settings.archive_max_snapshots :]

        texts = {}
        for index, capture in enumerate(candidates):
            if index:
                time.sleep(FETCH_DELAY_SECONDS)
            try:
                # redirect captures (e.g. gov.uz -> gov.uz/oz) resolve to the target page
                response = requests.get(
                    RAW_CAPTURE_URL.format(timestamp=capture["timestamp"], url=url),
                    headers={"User-Agent": settings.user_agent},
                    timeout=ARCHIVE_TIMEOUT_SECONDS,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("Archived capture %s unavailable: %s", capture["timestamp"], exc)
                continue
            texts[capture["timestamp"]] = _extract_text(_response_html(response))
        return texts

    def _store_snapshots(
        self,
        domain_id: int,
        captures: list[dict],
        checks: list[CheckResult],
        texts: dict[str, str],
    ) -> None:
        try:
            self.snapshot_repository.delete_archived(domain_id)
            previous_text = None
            for capture, check in zip(captures, checks):
                text_content = texts.get(capture["timestamp"])
                # markup-only changes produce a new digest but the same text - skip those
                if text_content is None or text_content == previous_text:
                    continue
                self.snapshot_repository.insert_archived(
                    domain_id, text_content, capture["captured_at"], check.id
                )
                previous_text = text_content
        except PyMongoError as exc:
            logger.warning("Snapshot storage unavailable for domain %s: %s", domain_id, exc)


def import_history_in_background(domain_id: int) -> None:
    """Background-task body: needs its own session, the request's one is closed by now."""
    with _import_lock:
        db = SessionLocal()
        try:
            domain = db.get(Domain, domain_id)
            if domain is not None:
                ArchiveImportService(db).import_history(domain)
        except ArchiveUnavailableError as exc:
            logger.warning("Archive import skipped for domain %s: %s", domain_id, exc)
        except Exception:
            logger.exception("Archive import failed for domain %s", domain_id)
        finally:
            db.close()
