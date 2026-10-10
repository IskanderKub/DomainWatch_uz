# Tests for the application lifespan. Every Mongo call at runtime tolerates an
# outage, and startup has to behave the same way - otherwise an unreachable Mongo
# stops availability monitoring, which only needs PostgreSQL.
import asyncio
import logging

from pymongo.errors import ServerSelectionTimeoutError

import app.main as main


def _run_lifespan() -> None:
    async def run():
        async with main.lifespan(main.app):
            pass

    asyncio.run(run())


def _patch_startup(mocker):
    # the real calls would reach the developer's PostgreSQL/Mongo and start the
    # scheduler, so stub out everything the lifespan touches
    mocker.patch.object(main.Base.metadata, "create_all")
    mocker.patch.object(main, "upgrade_schema")
    mocker.patch.object(main, "ensure_schema_validator")
    mocker.patch.object(main, "stop_scheduler")
    mocker.patch.object(main.mongo_client, "close")
    return mocker.patch.object(main, "start_scheduler")


def test_startup_survives_mongo_being_unreachable(mocker, caplog):
    start_scheduler = _patch_startup(mocker)
    mocker.patch.object(
        main,
        "ensure_indexes",
        side_effect=ServerSelectionTimeoutError("connection refused"),
    )

    with caplog.at_level(logging.WARNING):
        _run_lifespan()

    # the API comes up and keeps checking availability, snapshots are just skipped
    start_scheduler.assert_called_once()
    assert "MongoDB unavailable at startup" in caplog.text


def test_startup_configures_mongo_when_it_is_reachable(mocker):
    start_scheduler = _patch_startup(mocker)
    ensure_indexes = mocker.patch.object(main, "ensure_indexes")

    _run_lifespan()

    ensure_indexes.assert_called_once()
    start_scheduler.assert_called_once()