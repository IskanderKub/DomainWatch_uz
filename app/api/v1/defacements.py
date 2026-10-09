# REST endpoint listing suspected defacements of a domain, with page diffs.
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.schemas.check import DefacementRead
from app.services.defacement_service import DefacementService
from app.services.domain_service import DomainService

router = APIRouter(prefix="/domains/{domain_id}/defacements", tags=["defacements"])


@router.get("", response_model=list[DefacementRead])
def list_defacements(
    domain_id: int,
    limit: int = Query(100, ge=1, le=10000),
    since: datetime | None = None,
    until: datetime | None = None,
    db: Session = Depends(get_db),
):
    domain = DomainService(db).get_domain(domain_id)
    if domain is None:
        raise HTTPException(status_code=404, detail="Domain not found")
    return DefacementService(db).list_for_domain(
        domain_id, limit=limit, since=since, until=until
    )
