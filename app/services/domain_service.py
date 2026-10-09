# Business logic for managing monitored domains (as opposed to raw DB access,
# which lives in DomainRepository).
from sqlalchemy.orm import Session

from app.models.sql_models import Domain
from app.repositories.domain_repository import DomainRepository


class DomainAlreadyExistsError(Exception):
    """Raised when trying to register a domain name that's already tracked."""

    pass


class DomainService:
    def __init__(self, db: Session, repository: DomainRepository | None = None):
        self.repository = repository or DomainRepository(db)

    def create_domain(self, name: str, url: str) -> Domain:
        if self.repository.get_by_name(name) is not None:
            raise DomainAlreadyExistsError(f"Domain '{name}' is already tracked")
        return self.repository.create(name=name, url=url)

    def list_domains(self, active_only: bool = False) -> list[Domain]:
        return self.repository.list(active_only=active_only)

    def get_domain(self, domain_id: int) -> Domain | None:
        return self.repository.get(domain_id)

    def delete_domain(self, domain: Domain) -> None:
        self.repository.delete(domain)
