from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import build_multi_favorite_timeline

VERSION = "2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"
APP = Path("app.py").read_text(encoding="utf-8")
VIEW = Path("cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE = Path("cupnavi_core/style_system.py").read_text(encoding="utf-8")


def _row(row, key, default=None):
    return row.get(key, default)


def _team(source):
    if not source or not str(source).startswith("team:"):
        return None
    return int(str(source).split(":", 1)[1])


def test_version_is_v467():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_timeline_merges_favorite_matches_in_time_order():
    matches = [
        {"id": 2, "scheduled_start": "2026-09-05T11:00:00", "pitch_number": 2, "home_source": "team:3", "away_source": "team:4"},
        {"id": 1, "scheduled_start": "2026-09-05T10:00:00", "pitch_number": 1, "home_source": "team:1", "away_source": "team:2"},
    ]
    result = build_multi_favorite_timeline(
        matches, [1, 3], now=datetime(2026, 9, 5, 9, 0),
        source_team_id=_team, row_value=_row,
    )
    assert [item["match"]["id"] for item in result["matches"]] == [1, 2]


def test_match_between_two_favorites_is_shown_once_and_tagged_with_both():
    matches = [
        {"id": 7, "scheduled_start": "2026-09-05T10:00:00", "pitch_number": 1, "home_source": "team:1", "away_source": "team:3"},
    ]
    result = build_multi_favorite_timeline(
        matches, [1, 3], now=datetime(2026, 9, 5, 9, 0),
        source_team_id=_team, row_value=_row,
    )
    assert len(result["matches"]) == 1
    assert result["matches"][0]["favorite_team_ids"] == (1, 3)


def test_nearby_favorite_matches_are_flagged():
    matches = [
        {"id": 1, "scheduled_start": "2026-09-05T10:00:00", "pitch_number": 1, "home_source": "team:1", "away_source": "team:2"},
        {"id": 2, "scheduled_start": "2026-09-05T10:45:00", "pitch_number": 2, "home_source": "team:3", "away_source": "team:4"},
    ]
    result = build_multi_favorite_timeline(
        matches, [1, 3], now=datetime(2026, 9, 5, 9, 0),
        source_team_id=_team, row_value=_row, proximity_minutes=60,
    )
    assert result["conflict_match_ids"] == {1, 2}


def test_distant_matches_are_not_flagged():
    matches = [
        {"id": 1, "scheduled_start": "2026-09-05T10:00:00", "pitch_number": 1, "home_source": "team:1", "away_source": "team:2"},
        {"id": 2, "scheduled_start": "2026-09-05T11:30:00", "pitch_number": 2, "home_source": "team:3", "away_source": "team:4"},
    ]
    result = build_multi_favorite_timeline(
        matches, [1, 3], now=datetime(2026, 9, 5, 9, 0),
        source_team_id=_team, row_value=_row, proximity_minutes=60,
    )
    assert result["conflict_match_ids"] == set()


def test_view_uses_loaded_matches_and_mobile_style():
    assert "build_multi_favorite_timeline(" in VIEW
    assert "published_matches," in VIEW
    assert '"**Mina lag · kommande**"' in VIEW
    assert "inom 60 minuter" in VIEW
    assert ".cn-favorite-timeline-row{" in STYLE
    assert "@media(max-width:360px)" in STYLE
