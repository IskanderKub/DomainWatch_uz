# REST endpoints for triggering and reading domain checks.
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.repositories.check_repository import CheckRepository
from app.repositories.snapshot_repository import SnapshotRepository
from app.schemas.check import CheckResultRead
from app.services.checker_service import CheckerService
from app.services.domain_service import DomainService

router = APIRouter(prefix="/domains/{domain_id}/checks", tags=["checks"])


@router.post("", response_model=CheckResultRead, status_code=201)
def trigger_check(domain_id: int, db: Session = Depends(get_db)):
    # runs synchronously - useful for testing a domain on demand, outside the
    # scheduler's regular interval (see app/core/scheduler.py)
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return CheckerService(db).check_domain(domain)


@router.get("", response_model=list[CheckResultRead])
def list_checks(
    domain_id: int,
    limit: int = Query(100, ge=1, le=10000),
    since: datetime | None = None,
    until: datetime | None = None,
    is_available: bool | None = None,
    db: Session = Depends(get_db),
):
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return CheckRepository(db).list_for_domain(
        domain_id, limit=limit, since=since, until=until, is_available=is_available
    )


@router.get("/{check_id}/snapshot")
def get_check_snapshot(
    domain_id: int,
    check_id: int,
    db: Session = Depends(get_db),
):
    # 1. Проверяем, существует ли сам домен
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")

    # 2. Проверяем, существует ли сама проверка в Postgres и принадлежит ли она этому домену
    check = CheckRepository(db).get_by_id(check_id)
    if check is None or check.domain_id != domain_id:
        raise HTTPException(
            status_code=404, detail="Check result not found for this domain"
        )

    # 3. Запрашиваем raw-текст снапшота из Mongo через SnapshotRepository
    snapshot_repo = SnapshotRepository()
    snapshot = snapshot_repo.get_by_check_id(check_id)
    if snapshot is None:
        raise HTTPException(
            status_code=404, detail="Snapshot content not found for this check"
        )

    return {
        "check_id": check_id,
        "domain_id": domain_id,
        "text_content": snapshot.get("text_content"),
        "checked_at": snapshot.get("checked_at"),
    }
