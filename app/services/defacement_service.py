# Builds a human-readable diff for every suspected-defacement check: the snapshot
# saved by that check is compared word-by-word with the snapshot that preceded it.
import difflib
import logging
from datetime import datetime

from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.models.sql_models import CheckResult
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.check import DefacementRead, DiffSegment

logger = logging.getLogger(__name__)

# how many unchanged words to keep around each change, so the UI shows some context
# without dumping the whole page
CONTEXT_WORDS = 8


def _trim_equal(words: list[str], is_first: bool, is_last: bool) -> str:
    if len(words) <= CONTEXT_WORDS * 2:
        return " ".join(words)
    if is_first:
        return "… " + " ".join(words[-CONTEXT_WORDS:])
    if is_last:
        return " ".join(words[:CONTEXT_WORDS]) + " …"
    return " ".join(words[:CONTEXT_WORDS]) + " … " + " ".join(words[-CONTEXT_WORDS:])


def build_diff(old_text: str, new_text: str) -> list[DiffSegment]:
    old_words = old_text.split()
    new_words = new_text.split()
    opcodes = difflib.SequenceMatcher(None, old_words, new_words, autojunk=False).get_opcodes()

    segments = []
    for index, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if tag == "equal":
            text = _trim_equal(
                old_words[i1:i2], is_first=index == 0, is_last=index == len(opcodes) - 1
            )
            segments.append(DiffSegment(op="equal", text=text))
            continue
        # "replace" is reported as a removal followed by an addition
        if tag in ("delete", "replace"):
            segments.append(DiffSegment(op="removed", text=" ".join(old_words[i1:i2])))
        if tag in ("insert", "replace"):
            segments.append(DiffSegment(op="added", text=" ".join(new_words[j1:j2])))
    return segments


class DefacementService:
    def __init__(self, db: Session, snapshot_repository: SnapshotRepository | None = None):
        self.db = db
        self.snapshot_repository = snapshot_repository or SnapshotRepository()

    def list_for_domain(
        self,
        domain_id: int,
        limit: int = 100,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[DefacementRead]:
        query = self.db.query(CheckResult).filter(
            CheckResult.domain_id == domain_id,
            CheckResult.is_suspected_defacement.is_(True),
        )
        if since is not None:
            query = query.filter(CheckResult.checked_at >= since)
        if until is not None:
            query = query.filter(CheckResult.checked_at < until)
        checks = query.order_by(CheckResult.checked_at.desc()).limit(limit).all()
        return [
            DefacementRead(
                check_id=check.id,
                checked_at=check.checked_at,
                similarity_ratio=check.similarity_ratio,
                diff=self._diff_for_check(check),
            )
            for check in checks
        ]

    def _diff_for_check(self, check: CheckResult) -> list[DiffSegment] | None:
        try:
            snapshot = self.snapshot_repository.get_by_check_id(check.id)
            if snapshot is None:
                return None
            previous = self.snapshot_repository.get_previous(
                check.domain_id, snapshot["checked_at"]
            )
        except PyMongoError as exc:
            logger.warning("Snapshot lookup failed for check %s: %s", check.id, exc)
            return None
        if previous is None:
            return None
        return build_diff(previous["text_content"], snapshot["text_content"])
