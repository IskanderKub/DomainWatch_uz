# Background scheduler that periodically re-checks every active domain,
# so monitoring keeps running without any external caller hitting the API.
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.core.config import settings
from app.core.postgres import SessionLocal
from app.services.checker_service import CheckerService
from app.services.domain_service import DomainService

logger = logging.getLogger(__name__)

# BackgroundScheduler runs jobs in a separate thread, alongside the FastAPI event loop
scheduler = BackgroundScheduler()


def check_all_active_domains() -> None:
    """Job body: open a fresh DB session, check every active domain, close the session."""
    db = SessionLocal()
    try:
        domains = DomainService(db).list_domains(active_only=True)
        checker = CheckerService(db)
        for domain in domains:
            try:
                checker.check_domain(domain)
            except Exception:
                # one domain failing (e.g. bad SSL cert) must not stop the rest of the batch
                logger.exception("Failed to check domain %s", domain.name)
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        check_all_active_domains,
        "interval",
        minutes=settings.check_interval_minutes,
        id="check_all_active_domains",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    # wait=False: don't block app shutdown waiting for an in-flight check to finish
    if scheduler.running:
        scheduler.shutdown(wait=False)
