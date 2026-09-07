from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import build_family_next_step

VERSION = "2026.09.07-497-MY-TEAMS-NOTICES-POLISH"
APP = Path("app.py").read_text(encoding="utf-8")
VIEW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def _row(row, key, default=None):
    return row.get(key, default)


def test_version_is_v468():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_family_next_step_picks_first_two_timeline_items():
    timeline = {
        "matches": [
            {"start": datetime(2026, 9, 5, 10, 0), "match": {"pitch_number": 1}, "favorite_team_ids": (1,)},
            {"start": datetime(2026, 9, 5, 10, 45), "match": {"pitch_number": 2}, "favorite_team_ids": (2,)},
        ]
    }
    result = build_family_next_step(
        timeline, now=datetime(2026, 9, 5, 9, 30), row_value=_row
    )
    assert result["minutes_until_next"] == 30
    assert result["gap_minutes"] == 45
    assert result["pitch_change"] is True
    assert result["from_pitch"] == 1
    assert result["to_pitch"] == 2
    assert result["tight_turnaround"] is True


def test_same_pitch_is_not_reported_as_change():
    timeline = {
        "matches": [
            {"start": datetime(2026, 9, 5, 10, 0), "match": {"pitch_number": 3}, "favorite_team_ids": (1,)},
            {"start": datetime(2026, 9, 5, 11, 15), "match": {"pitch_number": 3}, "favorite_team_ids": (2,)},
        ]
    }
    result = build_family_next_step(
        timeline, now=datetime(2026, 9, 5, 9, 0), row_value=_row
    )
    assert result["pitch_change"] is False
    assert result["gap_minutes"] == 75
    assert result["tight_turnaround"] is False


def test_empty_timeline_is_safe():
    result = build_family_next_step(
        {"matches": []}, now=datetime(2026, 9, 5, 9, 0), row_value=_row
    )
    assert result["next_item"] is None
    assert result["following_item"] is None


def test_view_has_family_next_card_and_no_new_db_dependency():
    assert "build_family_next_step(" in VIEW
    assert ">Nästa för familjen<" in VIEW
    assert '"byt plan' in VIEW
    assert "samma plan." in VIEW
    assert ".cn-family-next-card{" in STYLE
    family_block = VIEW[VIEW.index("build_family_next_step("):VIEW.index('st.markdown("**Mina lag · kommande**")')]
    # v469 intentionally adds lazy rule/travel reads only after a following
    # favourite match exists; the ordinary first-paint/single-team path remains clean.
    assert 'if _family_step["following_item"] is not None:' in family_block
    assert "SELECT * FROM schedule_rules WHERE tournament_id=?" in family_block
    assert "FROM pitch_travel_times WHERE tournament_id=?" in family_block
