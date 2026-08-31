from pathlib import Path

from cupnavi_core.admin_match_events_repository import (
    fetch_played_matches,
    fetch_team_match_stats,
    fetch_team_players,
)

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "admin_match_events_view.py").read_text(encoding="utf-8")
REPO = (ROOT / "cupnavi_core" / "admin_match_events_repository.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_and_boundary():
    assert VERSION == "2026.08.31-353-GROUP-FLOW-PITCH-TIMING"
    block = APP[APP.index('if admin_page == "Matchhändelser":'):APP.index('if admin_page == "Besöksstatistik":')]
    assert "render_admin_match_events_workspace(" in block
    assert "update_player_match_stats_if_unchanged(" in block
    assert "st.data_editor(" not in block
    assert "SELECT * FROM player_match_stats" not in block
    assert "update_player_match_stats_if_unchanged(" not in VIEW


def test_view_owns_event_ui_and_validation_contract():
    assert 'st.header("Matchhändelser")' in VIEW
    assert 'st.data_editor(' in VIEW
    assert 'prepare_changed_event_rows(' in VIEW
    assert 'validate_match_event_totals(' in VIEW
    assert 'event_validation["ok"]' in VIEW
    assert 'event_autosave_conflict_' in VIEW
    assert '✓ Händelser sparas automatiskt – ingen Spara-knapp behövs.' in VIEW
    assert 'build_event_player_rows(' in VIEW
    assert 'build_reporter_columns(' in VIEW


def test_repository_queries_use_supplied_reader():
    calls = []
    def reader(sql, params):
        calls.append((sql, params))
        return [dict(id=1)]

    assert fetch_played_matches(reader, 8) == [dict(id=1)]
    assert calls[-1][1] == (8,)
    assert "home_score IS NOT NULL" in calls[-1][0]

    assert fetch_team_players(reader, 3) == [dict(id=1)]
    assert calls[-1][1] == (3,)
    assert "ORDER BY player_number,name" in calls[-1][0]

    assert fetch_team_match_stats(reader, 9, 3) == [dict(id=1)]
    assert calls[-1][1] == (9, 3)
    assert "player_match_stats" in calls[-1][0]


def test_app_save_callback_keeps_conditional_write_and_commit():
    block = APP[APP.index("def _save_admin_match_event_updates"):APP.index("render_admin_match_events_workspace(")]
    assert "with db() as con:" in block
    assert "update_player_match_stats_if_unchanged(" in block
    assert "event_update[\"expected\"]" in block
    assert "con.commit()" in block
    assert '"saved_count"' in block
    assert '"conflict_count"' in block
