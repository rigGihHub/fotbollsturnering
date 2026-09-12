import sqlite3
from contextlib import contextmanager

import pytest

import cupnavi_api.schedule_proposal_repository as repository
from cupnavi_api.schedule_proposal import build_schedule_proposal, schedule_proposal_fingerprint


def _match(match_id=1, **overrides):
    row = {
        "id": match_id,
        "group_id": 1,
        "match_no": match_id,
        "round_no": match_id,
        "home_source": f"team:{match_id * 2 - 1}",
        "away_source": f"team:{match_id * 2}",
        "scheduled_start": None,
        "pitch_number": None,
        "schedule_locked": False,
        "home_score": None,
        "away_score": None,
    }
    row.update(overrides)
    return row


def _rules(**overrides):
    row = {
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 5,
        "minimum_team_rest_minutes": 30,
    }
    row.update(overrides)
    return row


def _windows(**overrides):
    row = {
        "pitch_number": 1,
        "play_date": "2026-09-12",
        "start_time": "09:00",
        "end_time": "12:00",
        "confirmed": 1,
    }
    row.update(overrides)
    return [row]


def test_fingerprint_changes_when_any_schedule_input_changes():
    matches = [_match()]
    rules = _rules()
    windows = _windows()
    baseline = schedule_proposal_fingerprint(matches, rules, windows)

    changed_match = [_match(scheduled_start="2026-09-12T09:00", pitch_number=1)]
    changed_rules = _rules(minimum_team_rest_minutes=45)
    changed_windows = _windows(start_time="09:15")

    assert schedule_proposal_fingerprint(changed_match, rules, windows) != baseline
    assert schedule_proposal_fingerprint(matches, changed_rules, windows) != baseline
    assert schedule_proposal_fingerprint(matches, rules, changed_windows) != baseline


def _database():
    con = sqlite3.connect(":memory:")
    con.row_factory = sqlite3.Row
    con.executescript(
        """
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,schedule_dirty INTEGER DEFAULT 0,is_published INTEGER DEFAULT 1);
        CREATE TABLE schedule_rules(
          tournament_id INTEGER PRIMARY KEY,pitch_count INTEGER,halves INTEGER,minutes_per_half INTEGER,
          halftime_minutes INTEGER,pitch_break_minutes INTEGER,minimum_team_rest_minutes INTEGER
        );
        CREATE TABLE matches(
          id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,stage TEXT,match_no INTEGER,round_no INTEGER,
          home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,schedule_locked INTEGER DEFAULT 0,
          schedule_published INTEGER DEFAULT 0,home_score INTEGER,away_score INTEGER
        );
        CREATE TABLE pitch_day_windows(
          tournament_id INTEGER,pitch_number INTEGER,play_date TEXT,start_time TEXT,end_time TEXT,confirmed INTEGER
        );
        INSERT INTO tournaments(id) VALUES(1);
        INSERT INTO schedule_rules VALUES(1,1,2,20,5,5,30);
        INSERT INTO pitch_day_windows VALUES(1,1,'2026-09-12','09:00','12:00',1);
        INSERT INTO matches(id,tournament_id,group_id,stage,match_no,round_no,home_source,away_source)
        VALUES(1,1,1,'group',1,1,'team:1','team:2');
        """
    )
    con.commit()
    return con


def _patch_repository(monkeypatch, con):
    @contextmanager
    def fake_connect():
        yield con

    monkeypatch.setattr(repository, "connect", fake_connect)
    monkeypatch.setattr(repository, "_has_tournament_access", lambda account_id, tournament_id: True)
    monkeypatch.setattr(repository, "admin_venues", lambda account_id, tournament_id: {"ok": True})
    monkeypatch.setattr(
        repository,
        "admin_schedule",
        lambda account_id, tournament_id: {
            "matches": [],
            "conflict_analysis": {"ok": True, "error_count": 0, "warning_count": 0, "conflicts": []},
        },
    )


def _current_fingerprint(con):
    matches, rules, windows = repository._load_source(con, 1)
    return build_schedule_proposal(matches, rules, windows)["fingerprint"]


def test_apply_writes_server_rebuilt_placement_and_marks_schedule_dirty(monkeypatch):
    con = _database()
    _patch_repository(monkeypatch, con)
    fingerprint = _current_fingerprint(con)

    result = repository.apply_schedule_proposal(7, 1, fingerprint)

    row = con.execute("SELECT scheduled_start,pitch_number,schedule_published FROM matches WHERE id=1").fetchone()
    tournament = con.execute("SELECT schedule_dirty,is_published FROM tournaments WHERE id=1").fetchone()
    assert result["applied"] is True
    assert result["applied_count"] == 1
    assert row["scheduled_start"] == "2026-09-12T09:00"
    assert row["pitch_number"] == 1
    assert row["schedule_published"] == 0
    assert tournament["schedule_dirty"] == 1
    assert tournament["is_published"] == 0


def test_apply_rejects_stale_fingerprint_without_writing(monkeypatch):
    con = _database()
    _patch_repository(monkeypatch, con)
    fingerprint = _current_fingerprint(con)
    con.execute("UPDATE schedule_rules SET minimum_team_rest_minutes=45 WHERE tournament_id=1")
    con.commit()

    with pytest.raises(repository.ProposalStaleError):
        repository.apply_schedule_proposal(7, 1, fingerprint)

    row = con.execute("SELECT scheduled_start,pitch_number FROM matches WHERE id=1").fetchone()
    assert row["scheduled_start"] is None
    assert row["pitch_number"] is None
