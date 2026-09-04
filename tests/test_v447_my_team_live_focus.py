from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import (
    build_favorite_team_snapshot,
    favorite_team_primary_action_label,
)

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
VIEW = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")


def rv(row, key, default=None):
    return row.get(key, default)


def source_team_id(value):
    return int(str(value).split(":")[1]) if str(value).startswith("team:") else None


def test_v447_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_live_score_is_still_current_match_not_finished_result():
    now = datetime(2026, 9, 4, 10, 0)
    rows = [{
        "id": 9,
        "scheduled_start": "2026-09-04T09:45:00",
        "home_source": "team:1",
        "away_source": "team:2",
        "home_score": 1,
        "away_score": 0,
        "match_status": "live",
    }]
    snap = build_favorite_team_snapshot(rows, 1, now=now, source_team_id=source_team_id, row_value=rv)
    assert snap["next_match"]["id"] == 9
    assert snap["latest_match"] is None
    assert snap["played_count"] == 0
    assert favorite_team_primary_action_label(rows[0], now=now, row_value=rv) == "⚽ Följ matchen nu"


def test_primary_action_adapts_for_halftime_and_imminent_match():
    now = datetime(2026, 9, 4, 10, 0)
    halftime = {"scheduled_start": "2026-09-04T09:45:00", "match_status": "halftime"}
    imminent = {"scheduled_start": "2026-09-04T10:09:00", "match_status": "not_started"}
    assert favorite_team_primary_action_label(halftime, now=now, row_value=rv) == "⚽ Öppna matchen · paus"
    assert favorite_team_primary_action_label(imminent, now=now, row_value=rv) == "⚽ Nästa match om 9 min"


def test_directions_is_first_screen_but_remains_lazy():
    action = VIEW.index("_primary_match_action = favorite_team_primary_action_label")
    directions = VIEW.index('f"📍 Hitta till {public_pitch_label(favorite_next)}"')
    schedule = VIEW.index("_team_sections = favorite_team_match_sections")
    assert action < directions < schedule
    direction_block = VIEW[directions:schedule]
    assert "if show_directions:" in direction_block
    assert "venue_direction = one_row(" in direction_block
