# Unit tests for DomainService, against a real (in-memory SQLite) session.
import pytest

from app.services.domain_service import DomainAlreadyExistsError, DomainService
from tests.fakes import FakeSnapshotRepository


def test_create_domain(db_session):
    service = DomainService(db_session)

    domain = service.create_domain(name="example.uz", url="https://example.uz")

    assert domain.id is not None
    assert domain.name == "example.uz"
    assert domain.is_active is True


def test_create_domain_duplicate_name_raises(db_session):
    service = DomainService(db_session)
    service.create_domain(name="example.uz", url="https://example.uz")

    with pytest.raises(DomainAlreadyExistsError):
        service.create_domain(name="example.uz", url="https://example.uz")


def test_list_domains(db_session):
    service = DomainService(db_session)
    service.create_domain(name="a.uz", url="https://a.uz")
    service.create_domain(name="b.uz", url="https://b.uz")

    domains = service.list_domains()

    assert [d.name for d in domains] == ["a.uz", "b.uz"]


def test_get_and_delete_domain(db_session):
    service = DomainService(db_session)
    created = service.create_domain(name="example.uz", url="https://example.uz")

    fetched = service.get_domain(created.id)
    assert fetched is not None

    service.delete_domain(fetched)
    assert service.get_domain(created.id) is None


def test_delete_domain_also_removes_its_snapshots(db_session):
    # Postgres drops the check history through cascade="all, delete-orphan", but
    # MongoDB has no foreign key to domains, so its documents need removing explicitly
    snapshot_repo = FakeSnapshotRepository()
    service = DomainService(db_session, snapshot_repository=snapshot_repo)
    kept = service.create_domain(name="keep.uz", url="https://keep.uz")
    removed = service.create_domain(name="gone.uz", url="https://gone.uz")
    snapshot_repo.save(kept.id, "still monitored")
    snapshot_repo.save(removed.id, "about to go")

    service.delete_domain(removed)

    assert snapshot_repo.get_latest(removed.id) is None
    assert snapshot_repo.get_latest(kept.id)["text_content"] == "still monitored"


def test_delete_domain_survives_mongo_failure(db_session):
    # a Mongo outage must not block the domain from being deleted
    from pymongo.errors import ServerSelectionTimeoutError

    class BrokenSnapshotRepository(FakeSnapshotRepository):
        def delete_for_domain(self, domain_id: int) -> int:
            raise ServerSelectionTimeoutError("mongo is down")

    service = DomainService(db_session, snapshot_repository=BrokenSnapshotRepository())
    domain = service.create_domain(name="example.uz", url="https://example.uz")

    service.delete_domain(domain)

    assert service.get_domain(domain.id) is None


def test_set_active_pauses_and_resumes(db_session):
    service = DomainService(db_session)
    domain = service.create_domain(name="pause.uz", url="https://pause.uz")

    service.set_active(domain, False)
    assert service.list_domains(active_only=True) == []
    assert len(service.list_domains()) == 1

    service.set_active(domain, True)
    assert len(service.list_domains(active_only=True)) == 1


def test_scheduler_batch_survives_a_failed_commit(db_session, mocker):
    # when one domain's check fails mid-commit, the session is left needing a
    # rollback. Without one, every later domain in the same batch raises
    # PendingRollbackError and monitoring silently stops until the next restart.
    from app.core import scheduler as scheduler_module
    from app.models.sql_models import CheckResult

    service = DomainService(db_session)
    service.create_domain(name="first.uz", url="https://first.uz")
    service.create_domain(name="second.uz", url="https://second.uz")

    class FlakyChecker:
        def __init__(self, db):
            self.db = db

        def check_domain(self, domain):
            # is_available is NOT NULL, so the first domain fails on commit
            is_available = None if domain.name == "first.uz" else True
            self.db.add(CheckResult(domain_id=domain.id, is_available=is_available))
            self.db.commit()

    mocker.patch.object(scheduler_module, "SessionLocal", lambda: db_session)
    mocker.patch.object(scheduler_module, "CheckerService", FlakyChecker)
    mocker.patch.object(db_session, "close", lambda: None)

    scheduler_module.check_all_active_domains()

    # the second domain was still checked and its result stored
    stored = db_session.query(CheckResult).all()
    assert [c.domain_id for c in stored] == [2]
