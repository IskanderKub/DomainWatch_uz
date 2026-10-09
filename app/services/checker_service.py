# Core business logic: fetch a domain's page, extract its text, compare it against
# the previous snapshot, and record the result as a CheckResult row.
import difflib
import time
import logging
import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from pymongo.errors import PyMongoError
from app.core.config import settings
from app.models.sql_models import CheckResult, Domain
from app.repositories.check_repository import CheckRepository
from app.repositories.snapshot_repository import SnapshotRepository

logger = logging.getLogger(__name__)


def _extract_text(html: str) -> str:
    # strip tags/scripts/styles down to plain visible text, so markup churn
    # (e.g. a rebuilt <div> with the same content) doesn't look like a content change
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator=" ", strip=True)


def _similarity(old_text: str, new_text: str) -> float:
    # ratio() returns 0..1, where 1.0 means the texts are identical
    return difflib.SequenceMatcher(None, old_text, new_text).ratio()


class CheckerService:
    def __init__(
        self,
        db: Session,
        check_repository: CheckRepository | None = None,
        snapshot_repository: SnapshotRepository | None = None,
    ):
        self.db = db
        # repositories are injectable so tests can swap in fakes without a real DB/Mongo
        self.check_repository = check_repository or CheckRepository(db)
        self.snapshot_repository = snapshot_repository or SnapshotRepository()

    def check_domain(self, domain: Domain) -> CheckResult:
        started_at = time.monotonic()
        snapshot_id = None
        try:
            response = requests.get(domain.url, timeout=settings.check_timeout_seconds)
            response_time_ms = (time.monotonic() - started_at) * 1000

            similarity_ratio = None
            has_global_changes = False
            if response.ok:
                text_content = _extract_text(response.text)
                try:
                    previous_snapshot = self.snapshot_repository.get_latest(domain.id)
                    if previous_snapshot is not None:
                        # only compare/flag from the second check onward - there's nothing
                        # to compare the very first snapshot against
                        similarity_ratio = _similarity(
                            previous_snapshot["text_content"], text_content
                        )
                        has_global_changes = (
                            similarity_ratio < settings.content_change_threshold
                        )

                        # always store the new snapshot, even if this check flagged global
                        # changes, so the next check compares against the latest known content
                    snapshot_id = self.snapshot_repository.save(domain.id, text_content)
                except PyMongoError as exc:
                    logger.warning(
                        "Snapshot storage unavailable for domain %s: %s", domain.id, exc
                    )
            check = CheckResult(
                domain_id=domain.id,
                is_available=response.ok,
                status_code=response.status_code,
                response_time_ms=response_time_ms,
                similarity_ratio=similarity_ratio,
                has_global_changes=has_global_changes,
            )
        except requests.RequestException as exc:
            # network failure, timeout, DNS error, etc. - domain is simply unavailable
            check = CheckResult(
                domain_id=domain.id,
                is_available=False,
                status_code=None,
                response_time_ms=None,
                similarity_ratio=None,
                has_global_changes=False,
                error_message=str(exc),
            )

        check = self.check_repository.create(check)

        if snapshot_id is not None:
            try:
                self.snapshot_repository.attach_check_id(snapshot_id, check.id)
            except PyMongoError as exc:
                logger.warning("Failed to link snapshot to check %s: %s", check.id, exc)

        return check
