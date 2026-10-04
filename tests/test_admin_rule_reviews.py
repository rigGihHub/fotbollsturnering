import sqlite3

import pytest

from cupnavi_api.rules_admin_repository import admin_rules, update_rules


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "rules.db"
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    monkeypatch.setattr("cupnavi_api.rules_admin_repository._has_tournament_access", lambda account, cup: account == 1)
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE tournaments(id INTEGER PRIMARY KEY,sport TEXT,points_win INTEGER,
                points_draw INTEGER,points_loss INTEGER,table_tiebreak TEXT,schedule_dirty INTEGER,arrangement_type TEXT);
            INSERT INTO tournaments VALUES(1,'Fotboll',3,1,0,'Målskillnad först',0,'tournament');
            CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY,halves INTEGER DEFAULT 2,
                minutes_per_half INTEGER DEFAULT 20,halftime_minutes INTEGER DEFAULT 5,
                pitch_break_minutes INTEGER DEFAULT 5,minimum_team_rest_minutes INTEGER DEFAULT 45,
                avoid_consecutive_matches INTEGER DEFAULT 1,consecutive_match_break_minutes INTEGER DEFAULT 15);
            INSERT INTO schedule_rules(tournament_id) VALUES(1);
            CREATE TABLE matches(tournament_id INTEGER,scheduled_start TEXT,home_score INTEGER,away_score INTEGER);
            INSERT INTO matches VALUES(1,'2026-10-04T09:00',NULL,NULL);
        """)
    return path


def test_review_is_not_inferred_from_defaults_and_survives_reload(database):
    assert admin_rules(1, 1)["rules_reviewed"] is False
    saved = update_rules(1, 1, {})
    assert saved["rules_reviewed"] is True
    assert saved["schedule_dirty"] is False
    assert admin_rules(1, 1)["rules_reviewed_at"] == saved["rules_reviewed_at"]


def test_zero_half_time_is_preserved_and_timing_requires_schedule_check(database):
    saved = update_rules(1, 1, {"halves": 2, "minutes_per_half": 15, "halftime_minutes": 0})
    assert saved["halftime_minutes"] == 0
    assert saved["match_duration_minutes"] == 30
    assert saved["rules_reviewed"] and saved["schedule_dirty"]


def test_changed_rules_from_other_writer_invalidate_review(database):
    update_rules(1, 1, {})
    with sqlite3.connect(database) as con:
        con.execute("UPDATE schedule_rules SET minimum_team_rest_minutes=60 WHERE tournament_id=1")
    current = admin_rules(1, 1)
    assert current["rules_reviewed"] is False
    assert current["rules_reviewed_at"] is None


def test_failed_save_does_not_claim_review(database):
    with pytest.raises(ValueError):
        update_rules(1, 1, {"minutes_per_half": 0})
    assert admin_rules(1, 1)["rules_reviewed"] is False
    assert admin_rules(2, 1) is None
