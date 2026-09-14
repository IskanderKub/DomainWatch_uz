# Shared pytest fixtures: an in-memory SQLite DB and a FastAPI test client wired
# to it, so the test suite never needs a real PostgreSQL/MongoDB instance running.
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_db
from app.api.v1 import router as api_v1_router
from app.core.postgres import Base

# StaticPool + check_same_thread=False: keep a single SQLite in-memory connection
# alive and shared across threads for the whole test, instead of a fresh (empty) DB
# per connection, which is SQLite's normal in-memory behaviour.
test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(autouse=True)
def _tables():
    # fresh schema for every test, so tests can't leak state into each other
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def db_session():
    session = TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session):
    # a minimal app with just the v1 router - avoids app.main's lifespan, which
    # would otherwise try to connect to a real Postgres/Mongo and start the scheduler
    app = FastAPI()
    app.include_router(api_v1_router)
    app.dependency_overrides[get_db] = lambda: db_session

    with TestClient(app) as test_client:
        yield test_client


