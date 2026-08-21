import sqlite3

from cupnavi_core.health import collect_database_health
from cupnavi_core.migrations import apply_migrations


def _full_minimal_schema(con):
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY);
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER);
        CREATE TABLE players(id INTEGER PRIMARY KEY,team_id INTEGER);
        CREATE TABLE referees(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE brackets(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,scheduled_start TEXT);
        CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER);
        CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY);
        CREATE TABLE feedback(id INTEGER PRIMARY KEY,tournament_id INTEGER);
        CREATE TABLE offers(id INTEGER PRIMARY KEY,tournament_id INTEGER,active INTEGER,sort_order INTEGER);
        """
    )


def test_health_is_ok_after_migrations():
    con = sqlite3.connect(":memory:")
    _full_minimal_schema(con)
    apply_migrations(con)
    health = collect_database_health(con)
    assert health["ok"]
    assert not health["missing_tables"]
