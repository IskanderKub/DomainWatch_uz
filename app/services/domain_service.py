# Business logic for managing monitored domains (as opposed to raw DB access,
# which lives in DomainRepository).
import logging

from pymongo.errors import PyMongoError
from sqlalchemy.orm import Session

from app.models.sql_models import Domain
from app.repositories.domain_repository import DomainRepository
from app.repositories.snapshot_repository import SnapshotRepository

logger = logging.getLogger(__name__)


class DomainAlreadyExistsError(Exception):
    """Raised when trying to register a domain name that's already tracked."""

    pass


class DomainService:
    def __init__(
        self,
        db: Session,
        repository: DomainRepository | None = None,
        snapshot_repository: SnapshotRepository | None = None,
    ):
        self.repository = repository or DomainRepository(db)
        # injectable so tests can swap in a fake instead of a real MongoDB
        self.snapshot_repository = snapshot_repository or SnapshotRepository()

    def create_domain(self, name: str, url: str) -> Domain:
        if self.repository.get_by_name(name) is not None:
            raise DomainAlreadyExistsError(f"Domain '{name}' is already tracked")
        return self.repository.create(name=name, url=url)

    def list_domains(self, active_only: bool = False) -> list[Domain]:
        return self.repository.list(active_only=active_only)

    def get_domain(self, domain_id: int) -> Domain | None:
        return self.repository.get(domain_id)

    def set_active(self, domain: Domain, is_active: bool) -> Domain:
        """Pause or resume monitoring without losing the domain's check history."""
        return self.repository.set_active(domain, is_active)

    def delete_domain(self, domain: Domain) -> None:
        # Mongo is cleared first: if the Postgres row went first and Mongo then failed,
        # domain.id would be gone and nothing could say which snapshots to remove.
        # A Mongo outage must not block the delete, so it is logged and we carry on.
        try:
            self.snapshot_repository.delete_for_domain(domain.id)
        except PyMongoError as exc:
            logger.warning(
                "Failed to delete snapshots for domain %s: %s", domain.id, exc
            )
        self.repository.delete(domain)
