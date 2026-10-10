from datetime import datetime, timezone

from app.core.config import settings
from app.repositories.snapshot_repository import _content_hash


class FakeSnapshotRepository:
    def __init__(self):
        self.documents = []
        self._next_id = 0

    def save(self, domain_id: int, text_content: str):
        now = datetime.now(timezone.utc)
        # mirrors SnapshotRepository.save: truncate first, then hash what we store
        text_content = text_content[: settings.snapshot_max_text_length]
        content_hash = _content_hash(text_content)
        previous = self.get_latest(domain_id)
        if (
            previous is not None
            and previous.get("content_hash") == content_hash
            and previous.get("source") != "archive"
        ):
            previous["last_seen_at"] = now
            previous["seen_count"] += 1
            return previous["_id"]

        _id = self._next_id
        self._next_id += 1
        self.documents.append(
            {
                "domain_id": domain_id,
                "checked_at": now,
                "last_seen_at": now,
                "text_content": text_content,
                "content_hash": content_hash,
                "seen_count": 1,
                "_id": _id,
            }
        )
        return _id

    def get_latest(self, domain_id: int) -> dict | None:
        matching = []
        for doc in self.documents:
            if doc["domain_id"] == domain_id:
                matching.append(doc)

        if not matching:
            return None
        # same tiebreaker as SnapshotRepository.get_latest: _id decides when two
        # snapshots share a last_seen_at
        return max(matching, key=lambda doc: (doc["last_seen_at"], doc["_id"]))

    def insert_archived(
        self, domain_id: int, text_content: str, captured_at: datetime, check_id: int
    ):
        _id = self._next_id
        self._next_id += 1
        self.documents.append(
            {
                "domain_id": domain_id,
                "checked_at": captured_at,
                "last_seen_at": captured_at,
                "text_content": text_content,
                "content_hash": _content_hash(text_content),
                "seen_count": 1,
                "check_ids": [check_id],
                "source": "archive",
                "_id": _id,
            }
        )
        return _id

    def delete_archived(self, domain_id: int) -> None:
        self.documents = [
            doc
            for doc in self.documents
            if not (doc["domain_id"] == domain_id and doc.get("source") == "archive")
        ]

    def attach_check_id(self, snapshot_id: int, check_id: int) -> None:
        for doc in self.documents:
            if doc["_id"] == snapshot_id:
                check_ids = doc.setdefault("check_ids", [])
                if check_id not in check_ids:
                    check_ids.append(check_id)
                break

    def get_by_check_id(self, check_id: int) -> dict | None:
        for doc in self.documents:
            if check_id in doc.get("check_ids", []) or doc.get("check_id") == check_id:
                return doc
        return None

    def get_previous(self, domain_id: int, before: datetime) -> dict | None:
        matching = [
            doc
            for doc in self.documents
            if doc["domain_id"] == domain_id and doc["checked_at"] < before
        ]
        if not matching:
            return None
        return max(matching, key=lambda doc: doc["checked_at"])

    def delete_for_domain(self, domain_id: int) -> int:
        remaining = [doc for doc in self.documents if doc["domain_id"] != domain_id]
        deleted = len(self.documents) - len(remaining)
        self.documents = remaining
        return deleted
