import sqlite3
from pathlib import Path

from cupnavi_core.migrations import apply_migrations, LATEST_SCHEMA_VERSION
from cupnavi_core.push_notification_service import goal_push_events, enqueue_goal_push_events

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _db_at_v24():
    con = sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=ON")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    con.execute("CREATE TABLE teams(id INTEGER PRIMARY KEY, tournament_id INTEGER)")
    con.execute("CREATE TABLE matches(id INTEGER PRIMARY KEY, tournament_id INTEGER)")
    con.execute("CREATE TABLE cupnavi_schema_migrations(version INTEGER PRIMARY KEY,name TEXT NOT NULL,applied_at TEXT NOT NULL)")
    con.execute("INSERT INTO cupnavi_schema_migrations VALUES(24,'fixture','now')")
    return con


def test_v264_schema_is_push_provider_neutral():
    con = _db_at_v24()
    assert apply_migrations(con) == [25, 26]
    tables = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"web_push_subscriptions", "push_notification_outbox"} <= tables
    cols = {r[1] for r in con.execute("PRAGMA table_info(web_push_subscriptions)")}
    assert {"endpoint", "endpoint_hash", "p256dh", "auth", "notify_goals"} <= cols
    assert LATEST_SCHEMA_VERSION == 26


def test_goal_event_targets_only_scoring_team_and_is_idempotent():
    con = _db_at_v24(); apply_migrations(con)
    con.execute("INSERT INTO tournaments(id) VALUES(1)")
    con.executemany("INSERT INTO teams VALUES(?,1)", [(10,), (20,)])
    con.execute("INSERT INTO matches VALUES(99,1)")
    kwargs = dict(
        tournament_id=1, match_id=99,
        home_team_id=10, away_team_id=20,
        home_team_name="Hemma", away_team_name="Borta",
        old_home_score=0, old_away_score=0,
        new_home_score=1, new_away_score=0,
    )
    events = goal_push_events(**kwargs)
    assert len(events) == 1
    assert events[0]["team_id"] == 10
    assert events[0]["event_type"] == "goal"
    assert enqueue_goal_push_events(con, **kwargs) == 1
    assert enqueue_goal_push_events(con, **kwargs) == 0


def test_score_correction_does_not_create_goal_push():
    assert goal_push_events(
        tournament_id=1, match_id=1,
        home_team_id=10, away_team_id=20,
        home_team_name="A", away_team_name="B",
        old_home_score=2, old_away_score=1,
        new_home_score=1, new_away_score=1,
    ) == []


def test_all_primary_result_writes_enqueue_goal_push_in_write_transaction():
    assert APP.count("enqueue_goal_push_events(con") >= 3
    assert "_goal_push_kwargs" in APP
