from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_quick_score_buttons_use_pre_rerun_callbacks():
    assert "def _adjust_quick_score" in VIEW
    assert "on_click=_adjust_quick_score" in VIEW
    assert "def _reset_quick_score" in VIEW
    assert "on_click=_reset_quick_score" in VIEW
    assert 'st.session_state[draft_key][0] = max(0, quick_home_score - 1); st.rerun()' not in VIEW
    assert 'st.session_state[draft_key][1] = quick_away_score + 1; st.rerun()' not in VIEW


def test_save_and_status_use_single_normal_widget_rerun():
    assert "def _save_quick_result_callback" in VIEW
    assert "on_click=_save_quick_result_callback" in VIEW
    assert "def _set_match_status_callback" in VIEW
    assert "on_click=_set_match_status_callback" in VIEW
    assert 'st.session_state["reporter_result_warning"]' in VIEW


def test_player_navigation_does_not_force_second_rerun():
    assert "on_click=_set_session_value" in VIEW
