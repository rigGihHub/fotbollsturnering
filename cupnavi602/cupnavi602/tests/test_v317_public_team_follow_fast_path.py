from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import favorite_table_position_from_snapshot

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def _row_value(row, key, default=None):
    return row.get(key, default) if row else default


def test_followed_team_table_position_uses_loaded_snapshot_without_db_table_call():
    teams = [
        {"id": 1, "name": "Alpha", "group_id": 7},
        {"id": 2, "name": "Beta", "group_id": 7},
        {"id": 3, "name": "Gamma", "group_id": 8},
    ]
    matches = [
        {
            "group_id": 7,
            "stage": "Gruppspel",
            "home_source": "team:1",
            "away_source": "team:2",
            "home_score": 2,
            "away_score": 0,
        }
    ]
    tournament = {
        "points_win": 3,
        "points_draw": 1,
        "points_loss": 0,
        "table_tiebreak": "Målskillnad först",
    }
    assert favorite_table_position_from_snapshot(
        teams, matches, 1, tournament, row_value=_row_value
    ) == "1:a"
    assert favorite_table_position_from_snapshot(
        teams, matches, 2, tournament, row_value=_row_value
    ) == "2:a"


def test_public_team_follow_no_longer_calls_db_backed_calculate_table():
    assert "favorite_table_position_from_snapshot(" in VIEW
    assert "calculate_table(" not in VIEW
    assert "calculate_table=calculate_table" not in WORKSPACE


def test_venue_lookup_is_lazy_behind_directions_toggle():
    toggle = VIEW.index('f"📍 Hitta till {public_pitch_label(favorite_next)}"')
    venue_query = VIEW.index("SELECT url,label FROM venue_points")
    assert toggle < venue_query
    assert "if show_directions:" in VIEW[toggle:venue_query]
