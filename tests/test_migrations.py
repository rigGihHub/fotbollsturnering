import sqlite3

from cupnavi_core.migrations import (
    LATEST_SCHEMA_VERSION,
    apply_migrations,
    current_schema_version,
)


def _legacy_schema(con):
    # Minsta schema som indexmigrationen behöver.
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY);
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER);
        CREATE TABLE players(id INTEGER PRIMARY KEY,team_id INTEGER);
        CREATE TABLE referees(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE brackets(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            group_id INTEGER,
            bracket_id INTEGER,
            scheduled_start TEXT
        );
        CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER);
        CREATE TABLE feedback(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE offers(
            id INTEGER PRIMARY KEY,
            tournament_id INTEGER,
            active INTEGER,
            sort_order INTEGER
        );
        """
    )


def test_migrations_reach_latest_version():
    con = sqlite3.connect(":memory:")
    _legacy_schema(con)
    applied = apply_migrations(con)
    assert applied == [1, 2, 3]
    assert current_schema_version(con) == LATEST_SCHEMA_VERSION


def test_migrations_are_idempotent():
    con = sqlite3.connect(":memory:")
    _legacy_schema(con)
    apply_migrations(con)
    assert apply_migrations(con) == []


def test_performance_indexes_created():
    con = sqlite3.connect(":memory:")
    _legacy_schema(con)
    apply_migrations(con)
    indexes = {
        row[0]
        for row in con.execute(
            "SELECT name FROM sqlite_master WHERE type='index'"
        ).fetchall()
    }
    assert "idx_matches_tournament_start" in indexes
    assert "idx_offers_tournament_active_order" in indexes
    assert "idx_sponsors_tournament_active_order" in indexes
    assert "idx_functionaries_tournament_role" in indexes
