# Brings an existing database up to date with the models. create_all only creates
# missing tables, so column changes to tables that already exist are applied here.
# Every step checks the current schema first, so running it on each startup is safe.
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def upgrade_schema(engine: Engine) -> None:
    inspector = inspect(engine)
    if not inspector.has_table("check_results"):
        return  # fresh database - create_all builds the current schema
    columns = {column["name"] for column in inspector.get_columns("check_results")}

    with engine.begin() as connection:
        # the flag was renamed: it measures how much changed, not whether it was malicious
        if "is_suspected_defacement" in columns and "has_global_changes" not in columns:
            logger.info("Renaming check_results.is_suspected_defacement to has_global_changes")
            connection.execute(
                text(
                    "ALTER TABLE check_results "
                    "RENAME COLUMN is_suspected_defacement TO has_global_changes"
                )
            )
        if "source" not in columns:
            logger.info("Adding check_results.source")
            connection.execute(
                text(
                    "ALTER TABLE check_results "
                    "ADD COLUMN source VARCHAR NOT NULL DEFAULT 'live'"
                )
            )
