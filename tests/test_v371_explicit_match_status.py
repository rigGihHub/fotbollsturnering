from datetime import datetime
from pathlib import Path

from cupnavi_core.cup_day_dashboard import build_cup_day_snapshot
from cupnavi_core.match_status import (
    MATCH_FINISHED,
    MATCH_HALFTIME,
    MATCH_LIVE,
    MATCH_NOT_STARTED,
    match_status_label,
    normalize_match_status,
)
from cupnavi_core.public_match_feed_logic import classify_public_match_feed
from cupnavi_core.public_team_follow import build_favorite_team_snapshot

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
REPORTER = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
MIGRATIONS = (ROOT / "cupnavi_core" / "migrations.py").read_text(encoding="utf-8")


def rv(row, key, default=None):
    return row.get(key, default)


def source_team_id(value):
    return int(value.split(":")[1]) if str(value).startswith("team:") else None


def match(mid, start, status="not_started", hs=None, as_=None):
    return {
        "id": mid,
        "scheduled_start": start,
        "pitch_number": 1,
        "home_source": "team:1",
        "away_source": "team:2",
        "home_score": hs,
        "away_score": as_,
        "match_status": status,
    }


def test_status_normalization_and_result_force_finished():
    assert normalize_match_status("Pågår") == MATCH_LIVE
    assert normalize_match_status("paus") == MATCH_HALFTIME
    assert normalize_match_status(None) == MATCH_NOT_STARTED
    assert normalize_match_status("live", has_result=True) == MATCH_FINISHED
    assert match_status_label(MATCH_FINISHED) == "Slut"


def test_cupday_explicit_live_wins_over_clock():
    now = datetime(2026, 9, 1, 12, 0)
    rows = [match(1, "2026-09-01T08:00:00", status="live")]
    snap = build_cup_day_snapshot(rows, now=now, match_duration_minutes=30)
    assert [row["id"] for row in snap["live"]] == [1]
    assert snap["reporting_due"] == []


def test_cupday_overdue_not_started_is_not_claimed_live():
    now = datetime(2026, 9, 1, 12, 0)
    rows = [match(1, "2026-09-01T11:00:00", status="not_started")]
    snap = build_cup_day_snapshot(rows, now=now, match_duration_minutes=30, reporting_grace_minutes=10)
    assert snap["live"] == []
    assert [row["id"] for row in snap["reporting_due"]] == [1]


def test_public_feed_uses_explicit_live_and_pause():
    now = datetime(2026, 9, 1, 12, 0)
    rows = [
        match(1, "2026-09-01T08:00:00", status="live"),
        match(2, "2026-09-01T09:00:00", status="halftime"),
        match(3, "2026-09-01T13:00:00", status="not_started"),
    ]
    live, upcoming, recent = classify_public_match_feed(rows, now=now, match_duration_minutes=30)
    assert [r["id"] for r in live] == [1, 2]
    assert [r["id"] for r in upcoming] == [3]
    assert recent == []


def test_my_team_treats_active_match_as_current_even_if_scheduled_time_passed():
    now = datetime(2026, 9, 1, 12, 0)
    rows = [match(1, "2026-09-01T10:00:00", status="live")]
    snap = build_favorite_team_snapshot(rows, 1, now=now, source_team_id=source_team_id, row_value=rv)
    assert snap["next_match"]["id"] == 1


def test_reporter_has_explicit_four_state_controls():
    assert "Matchstatus:" in REPORTER
    assert '"▶ Pågår"' in REPORTER
    assert '"⏸ Paus"' in REPORTER
    assert '"■ Slut"' in REPORTER
    assert "set_match_status" in REPORTER


def test_result_save_marks_match_finished():
    assert "SET match_status='finished'" in APP
    assert "actual_finished_at=COALESCE(actual_finished_at,?)" in APP


def test_schema_v30_has_lifecycle_fields():
    assert "LATEST_SCHEMA_VERSION = 32" in MIGRATIONS
    assert "def ensure_v30_schema_compat" in MIGRATIONS
    assert "match_status TEXT NOT NULL DEFAULT 'not_started'" in MIGRATIONS
    assert "actual_started_at" in MIGRATIONS
    assert "actual_finished_at" in MIGRATIONS
