from datetime import datetime
from pathlib import Path

from cupnavi_core.public_team_follow import (
    build_favorite_team_snapshot,
    favorite_team_day_context,
    favorite_team_match_sections,
)

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
LOGIC = (ROOT / "cupnavi_core" / "public_team_follow.py").read_text(encoding="utf-8")


def rv(row, key, default=None):
    return row.get(key, default)


def source_team_id(value):
    return int(value.split(":")[1]) if str(value).startswith("team:") else None


def matches():
    return [
        {"id": 1, "scheduled_start": "2026-09-01T10:00:00", "home_source": "team:1", "away_source": "team:2", "home_score": 2, "away_score": 1},
        {"id": 2, "scheduled_start": "2026-09-01T12:00:00", "home_source": "team:3", "away_source": "team:1", "home_score": None, "away_score": None},
        {"id": 3, "scheduled_start": "2026-09-01T14:30:00", "home_source": "team:1", "away_source": "team:4", "home_score": None, "away_score": None},
    ]


def test_matchday_context_has_countdown_and_rest_from_existing_snapshot():
    now = datetime(2026, 9, 1, 11, 30)
    snapshot = build_favorite_team_snapshot(matches(), 1, now=now, source_team_id=source_team_id, row_value=rv)
    context = favorite_team_day_context(snapshot, now=now, row_value=rv)
    assert context["minutes_until"] == 30
    assert context["rest_minutes"] == 120


def test_sections_prioritize_recent_and_upcoming():
    now = datetime(2026, 9, 1, 11, 30)
    snapshot = build_favorite_team_snapshot(matches(), 1, now=now, source_team_id=source_team_id, row_value=rv)
    sections = favorite_team_match_sections(snapshot, now=now, row_value=rv)
    assert [m["id"] for m in sections["recent"]] == [1]
    assert [m["id"] for m in sections["upcoming"]] == [2, 3]


def test_matchcamp_hides_table_and_playoff_status():
    assert "show_competition_status: bool = True" in LOGIC
    assert "if not show_competition_status:" in LOGIC
    assert "show_competition_status=not _is_matchcamp" in VIEW


def test_mobile_team_page_surfaces_recent_and_upcoming_before_secondary_actions():
    recent = VIEW.index('st.markdown("**Senaste resultat**")')
    upcoming = VIEW.index('st.markdown("**Min cup · kommande matcher**")')
    actions = VIEW.index("team_action_1, team_action_2")
    assert recent < actions
    assert upcoming < actions
