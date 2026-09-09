from pathlib import Path

from cupnavi_core.public_team_follow import (
    favorite_table_position_label,
    favorite_team_group_id,
    find_possible_playoff,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "public_team_follow_view.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "cupnavi_core" / "public_workspace_view.py").read_text(encoding="utf-8")


def row_value(row, key, default=None):
    return row.get(key, default) if row else default


def source_team_id(source):
    try:
        return int(str(source).split(":", 1)[1])
    except Exception:
        return None


def test_follow_view_is_extracted_from_app():
    assert "from cupnavi_core.public_team_follow_view import render_public_team_follow" in APP
    assert "render_public_team_follow(" in WORKSPACE
    assert "Skicka verifieringsmejl" not in APP
    assert "Vägbeskrivning till" not in APP
    assert "Skicka verifieringsmejl" in VIEW
    assert "Vägbeskrivning till" in VIEW
    assert "public_force_team_filter_" in VIEW


def test_group_and_table_helpers_are_defensive():
    teams = [{"id": 1, "group_id": "7"}, {"id": 2, "group_id": None}]
    assert favorite_team_group_id(teams, 1, row_value=row_value) == 7
    assert favorite_team_group_id(teams, 2, row_value=row_value) is None
    assert favorite_team_group_id(teams, 999, row_value=row_value) is None
    assert favorite_table_position_label([(2, {}), (1, {})], 1) == "2:a"
    assert favorite_table_position_label([(2, {})], 1) == "–"


def test_possible_playoff_only_returns_unresolved_non_group_match_for_team():
    rows = [
        {"home_source": "team:1", "away_source": "team:2", "stage": "Gruppspel", "home_score": None, "away_score": None},
        {"home_source": "team:3", "away_source": "team:4", "stage": "Semifinal", "home_score": None, "away_score": None},
        {"home_source": "team:1", "away_source": "team:5", "stage": "Semifinal", "home_score": 2, "away_score": 1},
        {"home_source": "team:6", "away_source": "team:1", "stage": "Final", "home_score": None, "away_score": None},
    ]
    match = find_possible_playoff(rows, 1, source_team_id=source_team_id, row_value=row_value)
    assert match is rows[3]


def test_view_keeps_persistence_injected_instead_of_opening_database():
    assert "create_notification_subscription=create_notification_subscription" in APP
    assert "all_rows=all_rows" in APP
    assert "one_row=one_row" in APP
    assert "with db()" not in VIEW
    assert "sqlite" not in VIEW.lower()


def test_public_match_filter_view_uses_injected_source_resolver():
    source = (ROOT / "cupnavi_core" / "public_match_filters_view.py").read_text(encoding="utf-8")
    assert "source_team_id=_public_source_team_id" not in source
    assert source.count("source_team_id=source_team_id") >= 4
