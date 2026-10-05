from datetime import datetime, timezone
from app.repositories.snapshot_repository import _content_hash


class FakeSnapshotRepository:
    def __init__(self):
        self.documents = []

    def save(self, domain_id: int, text_content: str):
        now = datetime.now(timezone.utc)
        content_hash = _content_hash(text_content)
        previous = self.get_latest(domain_id)
        if previous is not None and previous.get("content_hash") == content_hash:
            previous["last_seen_at"] = now
            previous["seen_count"] += 1
            return previous["_id"]

        _id = len(self.documents)
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
        return max(matching, key=lambda doc: doc["last_seen_at"])

    def attach_check_id(self, snapshot_id: int, check_id: int) -> None:
        for doc in self.documents:
            if doc["_id"] == snapshot_id:
                doc["check_id"] = check_id
                break

    def get_by_check_id(self, check_id: int) -> dict | None:
        for doc in self.documents:
            if doc.get("check_id") == check_id:
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
