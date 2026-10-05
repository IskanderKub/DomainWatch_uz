# Data-access layer for page-text snapshots stored in MongoDB.
# Kept separate from PostgreSQL repositories since it uses a different driver (pymongo).
from datetime import datetime, timezone
import hashlib

from pymongo.collection import Collection

from app.core.mongo import snapshots_collection

from bson import ObjectId


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


class SnapshotRepository:
    def __init__(self, collection: Collection = snapshots_collection):
        self.collection = collection

    def save(self, domain_id: int, text_content: str) -> ObjectId:
        now = datetime.now(timezone.utc)
        content_hash = _content_hash(text_content)
        previous = self.get_latest(domain_id)

        if previous is not None and previous.get("content_hash") == content_hash:
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

    def attach_check_id(self, snapshot_id: ObjectId, check_id: int) -> None:
        self.collection.update_one(
            {"_id": snapshot_id},
            {"$set": {"check_id": check_id}},
        )

    def get_latest(self, domain_id: int) -> dict | None:
        # sort by last_seen_at descending and take the first document
        return self.collection.find_one(
            {"domain_id": domain_id}, sort=[("last_seen_at", -1)]
        )

    def get_by_check_id(self, check_id: int) -> dict | None:
        return self.collection.find_one({"check_id": check_id})

    def get_previous(self, domain_id: int, before: datetime) -> dict | None:
        # the snapshot that was current right before the given one was inserted
        return self.collection.find_one(
            {"domain_id": domain_id, "checked_at": {"$lt": before}},
            sort=[("checked_at", -1)],
        )
