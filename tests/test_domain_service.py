# Unit tests for DomainService, against a real (in-memory SQLite) session.
import pytest

from app.services.domain_service import DomainAlreadyExistsError, DomainService


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
