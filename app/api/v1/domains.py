# REST endpoints for managing monitored domains.
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.domain import DomainCreate, DomainRead
from app.services.domain_service import DomainAlreadyExistsError, DomainService

router = APIRouter(prefix="/domains", tags=["domains"])


@router.post("", response_model=DomainRead, status_code=201)
def create_domain(payload: DomainCreate, db: Session = Depends(get_db)):
    service = DomainService(db)
    try:
        return service.create_domain(name=payload.name, url=payload.url)
    except DomainAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("", response_model=list[DomainRead])
def list_domains(active_only: bool = False, db: Session = Depends(get_db)):
    return DomainService(db).list_domains(active_only=active_only)


@router.get("/{domain_id}", response_model=DomainRead)
def get_domain(domain_id: int, db: Session = Depends(get_db)):
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return domain


@router.delete("/{domain_id}", status_code=204)
def delete_domain(domain_id: int, db: Session = Depends(get_db)):
    service = DomainService(db)
    domain = service.get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    service.delete_domain(domain)
