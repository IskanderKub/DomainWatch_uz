# Tests for upgrade_schema: an old check_results table is brought up to date in place.
from sqlalchemy import create_engine, inspect, text

from app.core.migrations import upgrade_schema


def _columns(engine) -> set[str]:
    return {column["name"] for column in inspect(engine).get_columns("check_results")}


def test_upgrade_renames_flag_and_adds_source_keeping_rows():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE check_results ("
                "id INTEGER PRIMARY KEY, is_available BOOLEAN NOT NULL, "
                "is_suspected_defacement BOOLEAN NOT NULL)"
            )
        )
        connection.execute(text("INSERT INTO check_results VALUES (1, 1, 1)"))

    upgrade_schema(engine)

    columns = _columns(engine)
    assert "has_global_changes" in columns
    assert "is_suspected_defacement" not in columns
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT has_global_changes, source FROM check_results")
        ).one()
    assert row == (1, "live")


def test_upgrade_is_idempotent():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE check_results (id INTEGER PRIMARY KEY, "
                "has_global_changes BOOLEAN NOT NULL, source VARCHAR NOT NULL DEFAULT 'live')"
            )
        )

    upgrade_schema(engine)
    upgrade_schema(engine)

    assert _columns(engine) == {"id", "has_global_changes", "source"}


def test_upgrade_skips_fresh_database():
    engine = create_engine("sqlite:///:memory:")

    upgrade_schema(engine)

    assert not inspect(engine).has_table("check_results")
