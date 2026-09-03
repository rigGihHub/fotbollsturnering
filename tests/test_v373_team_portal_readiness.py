from datetime import datetime
from pathlib import Path

from cupnavi_core.team_portal_readiness import build_team_portal_readiness, readiness_icon

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "team_portal_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_readiness_marks_core_team_tasks():
    team = {"checked_in": 1, "kit_confirmed_at": "2026-09-01T08:00:00"}
    players = [{"id": 1}, {"id": 2}]
    matches = [
        {"id": 10, "scheduled_start": "2026-09-02T10:00:00"},
        {"id": 11, "scheduled_start": "2026-09-02T12:00:00"},
    ]
    roster_rows = [
        {"match_id": 10, "player_id": 1},
        {"match_id": 11, "player_id": 1},
    ]
    result = build_team_portal_readiness(
        team,
        players=players,
        team_matches=matches,
        roster_rows=roster_rows,
        enable_team_checkin=True,
        now=datetime(2026, 9, 1, 12, 0),
    )
    assert result["ready"] is True
    assert result["ready_count"] == 4
    assert result["actionable_count"] == 4
    assert result["todo_count"] == 0


def test_missing_match_rosters_are_counted_for_future_matches_only():
    team = {"checked_in": 1, "kit_confirmed_at": "yes"}
    players = [{"id": 1}]
    matches = [
        {"id": 9, "scheduled_start": "2026-08-31T10:00:00"},
        {"id": 10, "scheduled_start": "2026-09-02T10:00:00"},
        {"id": 11, "scheduled_start": "2026-09-02T12:00:00"},
    ]
    result = build_team_portal_readiness(
        team,
        players=players,
        team_matches=matches,
        roster_rows=[{"match_id": 10, "player_id": 1}],
        enable_team_checkin=True,
        now=datetime(2026, 9, 1, 12, 0),
    )
    item = next(item for item in result["items"] if item["key"] == "match_rosters")
    assert item["state"] == "todo"
    assert item["missing_count"] == 1
    assert item["future_count"] == 2


def test_no_schedule_is_waiting_not_failure():
    result = build_team_portal_readiness(
        {"checked_in": 1, "kit_confirmed_at": "yes"},
        players=[{"id": 1}],
        team_matches=[],
        roster_rows=[],
        enable_team_checkin=True,
        now=datetime(2026, 9, 1, 12, 0),
    )
    item = next(item for item in result["items"] if item["key"] == "match_rosters")
    assert item["state"] == "waiting"
    assert result["ready"] is True
    assert result["actionable_count"] == 3


def test_disabled_checkin_is_not_counted_as_missing():
    result = build_team_portal_readiness(
        {"checked_in": 0, "kit_confirmed_at": "yes"},
        players=[{"id": 1}],
        team_matches=[],
        roster_rows=[],
        enable_team_checkin=False,
        now=datetime(2026, 9, 1, 12, 0),
    )
    checkin = next(item for item in result["items"] if item["key"] == "checkin")
    assert checkin["state"] == "not_applicable"
    assert result["ready"] is True
    assert result["actionable_count"] == 2


def test_portal_shows_readiness_before_tabs_and_next_step():
    readiness_pos = VIEW.index('st.markdown("### Redo för cupdagen")')
    tabs_pos = VIEW.index('portal_tabs = st.tabs(["Lag & matcher", "Trupp", "Matchtrupper", message_tab_label])')
    assert readiness_pos < tabs_pos
    assert '"Nästa steg:' in VIEW
    assert "build_team_portal_readiness(" in VIEW
    assert 'f"Gå till fliken **{_next[\'tab\']}**."' in VIEW


def test_core_snapshot_is_fetched_once_and_reused_across_tabs():
    assert VIEW.count("fetch_team_players(deps.all_rows, team_id)") == 1
    assert VIEW.count("fetch_match_rosters(deps.all_rows, team_id)") == 1
    assert VIEW.count("fetch_portal_matches(") == 1


def test_readiness_icons_are_plain_and_clear():
    assert readiness_icon("ready") == "✅"
    assert readiness_icon("todo") == "○"
    assert readiness_icon("waiting") == "⏳"
