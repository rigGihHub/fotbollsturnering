from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text()
VERSION = "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_version_markers_are_current():
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "app.py").read_text()
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_next_match_helper_only_scans_later_unreported_matches():
    block = WORKSPACE.split("def _next_unreported_match_id", 1)[1].split("def _select_quick_score_match", 1)[0]
    assert "playable_matches[current_index + 1:]" in block
    assert 'row["home_score"] is None or row["away_score"] is None' in block
    assert "return int(row[\"id\"])" in block


def test_one_tap_next_match_uses_widget_callback_without_database_write():
    block = WORKSPACE.split("def _select_quick_score_match", 1)[1].split("def render_match_reporter_workspace", 1)[0]
    assert "st.session_state[widget_key] = int(match_id)" in block
    for forbidden in ("query_all(", "UPDATE ", "INSERT ", "DELETE ", "commit("):
        assert forbidden not in block


def test_next_match_shortcut_only_follows_persisted_result_and_skips_reported_matches():
    assert 'persisted_result = quick_match["home_score"] is not None and quick_match["away_score"] is not None' in WORKSPACE
    persisted = WORKSPACE.split("if persisted_result:", 1)[1].split('st.markdown("### ⚽ Livehändelser")', 1)[0]
    assert "_next_unreported_match_id(playable_matches, int(quick_match_id))" in persisted
    assert '"Nästa orapporterade match →"' in persisted
    assert "on_click=_select_quick_score_match" in persisted
    assert "args=(quick_score_widget_key, next_match_id)" in persisted
    assert "Inga fler orapporterade matcher senare i schemat" in persisted


def test_existing_score_and_event_paths_remain_present():
    assert '"✅ Spara resultat"' in WORKSPACE
    assert 'st.markdown("### ⚽ Livehändelser")' in WORKSPACE
    assert "_render_match_event_entry(" in WORKSPACE
    assert "save_quick_result" in WORKSPACE
