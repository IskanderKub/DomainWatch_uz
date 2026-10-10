# Data-access layer for page-text snapshots stored in MongoDB.
# Kept separate from PostgreSQL repositories since it uses a different driver (pymongo).
from datetime import datetime, timezone
import hashlib

from pymongo.collection import Collection

from app.core.config import settings
from app.core.mongo import snapshots_collection

from bson import ObjectId


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class SnapshotRepository:
    def __init__(self, collection: Collection | None = None):
        # resolved at call time, not at import: a module-level default binds the live
        # collection when this module is first imported, leaving tests nothing to swap
        self.collection = collection if collection is not None else snapshots_collection

    def save(self, domain_id: int, text_content: str) -> ObjectId:
        now = datetime.now(timezone.utc)
        # MongoDB rejects any document over 16 MB (BSON limit), so an unusually large
        # page would fail the insert outright. Truncate before hashing, so content_hash
        # always describes exactly what is stored and deduplication stays consistent.
        text_content = text_content[: settings.snapshot_max_text_length]
        content_hash = _content_hash(text_content)
        previous = self.get_latest(domain_id)

        # archive snapshots are never reused: a re-import deletes them (see delete_archived)
        if (
            previous is not None
            and previous.get("content_hash") == content_hash
            and previous.get("source") != "archive"
        ):
            self.collection.update_one(
                {"_id": previous["_id"]},
                {"$set": {"last_seen_at": now}, "$inc": {"seen_count": 1}},
            )
            return previous["_id"]

        result = self.collection.insert_one(
            {
                "domain_id": domain_id,
                "checked_at": now,
                "last_seen_at": now,
                "text_content": text_content,
                "content_hash": content_hash,
                "seen_count": 1,
            }
        )
        return result.inserted_id

    def insert_archived(
        self, domain_id: int, text_content: str, captured_at: datetime, check_id: int
    ) -> ObjectId:
        # last_seen_at is the capture time, so the TTL index expires it like any
        # snapshot that was last seen back then
        result = self.collection.insert_one(
            {
                "domain_id": domain_id,
                "checked_at": captured_at,
                "last_seen_at": captured_at,
                "text_content": text_content,
                "content_hash": _content_hash(text_content),
                "seen_count": 1,
                "check_ids": [check_id],
                "source": "archive",
            }
        )
        return result.inserted_id

    def delete_archived(self, domain_id: int) -> None:
        self.collection.delete_many({"domain_id": domain_id, "source": "archive"})

    def attach_check_id(self, snapshot_id: ObjectId, check_id: int) -> None:
        # checks that see unchanged content reuse the same snapshot (see save), so it
        # collects every check id - overwriting a single one would leave the earlier
        # checks (including the one that flagged global changes) without a snapshot
        self.collection.update_one(
            {"_id": snapshot_id},
            {"$addToSet": {"check_ids": check_id}},
        )

    def get_latest(self, domain_id: int) -> dict | None:
        # sort by last_seen_at descending and take the first document.
        # _id breaks ties: BSON stores dates at millisecond precision, so two snapshots
        # written in the same millisecond share a last_seen_at, and without a tiebreaker
        # the sort may return the older one - which check_domain would then compare
        # against, and save() would deduplicate against, as if it were current.
        # ObjectId grows monotonically within a process, so it orders them correctly.
        return self.collection.find_one(
            {"domain_id": domain_id}, sort=[("last_seen_at", -1), ("_id", -1)]
        )

    def get_by_check_id(self, check_id: int) -> dict | None:
        # check_id is the single-link field used by snapshots saved before check_ids
        return self.collection.find_one(
            {"$or": [{"check_ids": check_id}, {"check_id": check_id}]}
        )

    def get_previous(self, domain_id: int, before: datetime) -> dict | None:
        # the snapshot that was current right before the given one was inserted
        return self.collection.find_one(
            {"domain_id": domain_id, "checked_at": {"$lt": before}},
            sort=[("checked_at", -1)],
        )

    def delete_for_domain(self, domain_id: int) -> int:
        """Remove every snapshot of a domain, and return how many were deleted.

        Postgres drops a domain's check history through cascade="all, delete-orphan",
        but that only covers SQLAlchemy tables - MongoDB has no foreign key to the
        domains table, so its documents have to be removed explicitly.
        """
        return self.collection.delete_many({"domain_id": domain_id}).deleted_count
