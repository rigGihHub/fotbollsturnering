from pathlib import Path
from cupnavi_core.revision_import import build_match_revision_rows, merge_clock_into_scheduled_start

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VER = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v583_version_and_match_level_review_ui():
    assert "583-MATCH-LEVEL-REVISION-APPROVAL" in VER
    assert "Granska match för match" in APP
    assert "Välj alla säkra" in APP
    assert "Tillämpa valda matchändringar" in APP


def test_changed_unchanged_new_removed_are_classified():
    current = [
        {"id": 1, "phase": "group", "home": "A", "away": "B", "group": "Grupp A", "time": "2026-09-12T09:00", "scheduled_start": "2026-09-12T09:00:00", "venue": "Plan 1", "played": False},
        {"id": 2, "phase": "group", "home": "C", "away": "D", "group": "Grupp A", "time": "2026-09-12T10:00", "scheduled_start": "2026-09-12T10:00:00", "venue": "Plan 1", "played": False},
        {"id": 3, "phase": "group", "home": "E", "away": "F", "group": "Grupp A", "time": "2026-09-12T11:00", "scheduled_start": "2026-09-12T11:00:00", "venue": "Plan 1", "played": False},
    ]
    payload = {"matches": [
        {"home_team": "A", "away_team": "B", "group_name": "Grupp A", "time": "09:30", "venue": "Plan 2"},
        {"home_team": "C", "away_team": "D", "group_name": "Grupp A", "time": "10:00", "venue": "Plan 1"},
        {"home_team": "G", "away_team": "H", "group_name": "Grupp A", "time": "12:00", "venue": "Plan 1"},
    ]}
    rows = build_match_revision_rows(current, payload)
    statuses = [r["status"] for r in rows]
    assert statuses.count("changed") == 1
    assert statuses.count("unchanged") == 1
    assert statuses.count("new") == 1
    assert statuses.count("removed") == 1


def test_played_match_is_never_safe_to_apply():
    current = [{"id": 7, "phase": "group", "home": "A", "away": "B", "group": "A", "time": "09:00", "scheduled_start": "2026-09-12T09:00:00", "venue": "Plan 1", "played": True}]
    payload = {"matches": [{"home_team": "A", "away_team": "B", "group_name": "A", "time": "09:30", "venue": "Plan 1"}]}
    row = build_match_revision_rows(current, payload)[0]
    assert row["status"] == "changed"
    assert row["safe_to_apply"] is False
    assert "Re-check the played lock inside the write transaction" in APP


def test_time_change_keeps_existing_match_date():
    assert merge_clock_into_scheduled_start("2026-09-12T09:00:00", "10:45") == "2026-09-12T10:45:00"
    assert merge_clock_into_scheduled_start("", "10:45") is None


def test_new_and_removed_matches_are_not_automatically_applied():
    assert "De läggs inte till automatiskt" in APP
    assert "De tas inte bort automatiskt" in APP
    assert "Spelade matcher, nya matcher och borttagningar har inte ändrats" in APP
