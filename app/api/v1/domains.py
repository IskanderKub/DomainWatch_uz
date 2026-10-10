# REST endpoints for managing monitored domains.
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.core.config import settings
from app.schemas.domain import DomainCreate, DomainRead, DomainUpdate
from app.services.archive_service import import_history_in_background
from app.services.domain_service import DomainAlreadyExistsError, DomainService

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("", response_model=DomainRead, status_code=201)
def create_domain(
    payload: DomainCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    service = DomainService(db)
    try:
        domain = service.create_domain(name=payload.name, url=payload.url)
    except DomainAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if settings.archive_import_on_create:
        # runs after the response is sent - the archive takes minutes to answer
        background_tasks.add_task(import_history_in_background, domain.id)
    return domain


@router.get("", response_model=list[DomainRead])
def list_domains(active_only: bool = False, db: Session = Depends(get_db)):
    return DomainService(db).list_domains(active_only=active_only)


@router.get("/{domain_id}", response_model=DomainRead)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.patch("/{domain_id}", response_model=DomainRead)
def update_domain(domain_id: int, payload: DomainUpdate, db: Session = Depends(get_db)):
    # pausing keeps the domain and its history, unlike DELETE - the scheduler skips it
    # because it only picks up domains where is_active is true
    service = DomainService(db)
    domain = service.get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return service.set_active(domain, payload.is_active)


@router.delete("/{domain_id}", status_code=204)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    service = DomainService(db)
    domain = service.get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    service.delete_domain(domain)


@router.post("/{domain_id}/archive-import", status_code=202)
def import_archive_history(
    domain_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    # re-imports the Wayback Machine history, replacing the previous import
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    background_tasks.add_task(import_history_in_background, domain_id)
    return {"status": "started"}
