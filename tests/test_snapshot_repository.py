# Unit tests for SnapshotRepository against mongomock, which implements pymongo's
# API in memory - so these cover the real repository code (filters, sort, $inc,
# delete_many) without a running MongoDB, unlike FakeSnapshotRepository which
# reimplements that logic and can only verify itself.
from datetime import datetime, timedelta, timezone

import mongomock
import pytest

from app.core.config import settings
from app.repositories.snapshot_repository import SnapshotRepository, _content_hash


@pytest.fixture
def repository() -> SnapshotRepository:
    collection = mongomock.MongoClient().domainwatch.snapshots
    return SnapshotRepository(collection=collection)


def test_save_inserts_document_with_all_required_fields(repository):
    # the collection's $jsonSchema validator requires all six of these
    snapshot_id = repository.save(1, "Ministry of Finance")

    document = repository.collection.find_one({"_id": snapshot_id})
    assert document["domain_id"] == 1
    assert document["text_content"] == "Ministry of Finance"
    assert document["content_hash"] == _content_hash("Ministry of Finance")
    assert document["seen_count"] == 1
    assert document["checked_at"] is not None
    assert document["last_seen_at"] is not None


def test_save_deduplicates_identical_content(repository):
    first_id = repository.save(1, "same text")
    second_id = repository.save(1, "same text")

    assert first_id == second_id
    assert repository.collection.count_documents({}) == 1
    assert repository.collection.find_one({"_id": first_id})["seen_count"] == 2


def test_save_inserts_new_document_when_content_changes(repository):
    first_id = repository.save(1, "original text")
    second_id = repository.save(1, "Suspicious Activity")

    assert first_id != second_id
    assert repository.collection.count_documents({}) == 2
    # get_latest must return the newer one, so the next check compares against it
    assert repository.get_latest(1)["text_content"] == "Suspicious Activity"


def test_get_latest_breaks_timestamp_ties_by_id(repository, mocker):
    # BSON stores dates at millisecond precision, so two snapshots written in the
    # same millisecond share a last_seen_at. Time is frozen here to reproduce that
    # collision every run. get_latest must still return the newer snapshot - if it
    # returns the older one, the next check compares against stale content and
    # save() deduplicates against the wrong hash.
    frozen_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    mocker.patch(
        "app.repositories.snapshot_repository.datetime",
        **{"now.return_value": frozen_now},
    )

    first_id = repository.save(1, "original text")
    second_id = repository.save(1, "Suspicious Activity")

    stored = list(repository.collection.find({"domain_id": 1}))
    assert len({doc["last_seen_at"] for doc in stored}) == 1  # the tie is real
    assert first_id != second_id
    assert repository.get_latest(1)["_id"] == second_id


def test_save_truncates_text_over_the_configured_limit(repository):
    limit = settings.snapshot_max_text_length
    snapshot_id = repository.save(1, "x" * (limit + 5_000))

    stored = repository.collection.find_one({"_id": snapshot_id})["text_content"]
    assert len(stored) == limit


def test_truncated_text_is_hashed_after_truncation(repository):
    # two oversized pages differing only past the limit must dedupe to one document,
    # since what we store is identical - the hash has to describe the stored text
    limit = settings.snapshot_max_text_length
    first_id = repository.save(1, "x" * limit + "tail A")
    second_id = repository.save(1, "x" * limit + "tail B")

    assert first_id == second_id
    assert repository.collection.count_documents({}) == 1


def test_delete_for_domain_removes_only_that_domains_snapshots(repository):
    repository.save(1, "domain one, first page")
    repository.save(1, "domain one, second page")
    repository.save(2, "domain two")

    deleted = repository.delete_for_domain(1)

    assert deleted == 2
    assert repository.get_latest(1) is None
    assert repository.get_latest(2)["text_content"] == "domain two"


def test_delete_for_domain_on_unknown_domain_is_a_no_op(repository):
    repository.save(1, "text")

    assert repository.delete_for_domain(999) == 0
    assert repository.collection.count_documents({}) == 1


def test_attach_check_id_collects_every_check(repository):
    # unchanged content reuses one document, so the link has to be a set of ids:
    # overwriting a single field would leave earlier checks without a snapshot
    snapshot_id = repository.save(1, "unchanged page")
    repository.attach_check_id(snapshot_id, 10)
    repository.attach_check_id(snapshot_id, 11)

    assert repository.get_by_check_id(10)["_id"] == snapshot_id
    assert repository.get_by_check_id(11)["_id"] == snapshot_id


def test_get_previous_returns_the_snapshot_before_a_moment(repository):
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    repository.collection.insert_one(
        {
            "domain_id": 1,
            "checked_at": old,
            "last_seen_at": old,
            "text_content": "older page",
            "content_hash": _content_hash("older page"),
            "seen_count": 1,
        }
    )

    previous = repository.get_previous(1, old + timedelta(days=1))

    assert previous["text_content"] == "older page"
    assert repository.get_previous(1, old) is None


def test_get_latest_returns_none_for_unknown_domain(repository):
    assert repository.get_latest(42) is None
