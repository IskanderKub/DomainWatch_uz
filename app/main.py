# FastAPI application entrypoint.
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_v1_router
from app.core.migrations import upgrade_schema
from app.core.postgres import Base, engine
from app.core.mongo import ensure_indexes, ensure_schema_validator, mongo_client
from app.core.scheduler import start_scheduler, stop_scheduler


# uvicorn only configures its own loggers - without this, app.* log records
# (check outcomes, scheduler runs, Mongo failures) never reach the console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # create_all is idempotent (no-op for tables that already exist) - fine for a
    # pet project; a production service would use Alembic migrations instead
    Base.metadata.create_all(bind=engine)
    upgrade_schema(engine)
    ensure_indexes()
    ensure_schema_validator()
    start_scheduler()
    yield
    stop_scheduler()
    mongo_client.close()


app = FastAPI(title="DomainWatch.uz", lifespan=lifespan)
app.include_router(api_v1_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# mounted last so it never shadows the API routes/health check above -
# Starlette matches routes in registration order, and this is a catch-all
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
