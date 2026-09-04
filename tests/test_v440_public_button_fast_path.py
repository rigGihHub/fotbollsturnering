from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
WORKSPACE = (ROOT / "cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")


def test_v440_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_public_search_buttons_use_single_rerun_callbacks():
    assert "on_click=_clear_public_search" in WORKSPACE
    assert "on_click=_open_public_search_result" in WORKSPACE
    search_block = WORKSPACE[WORKSPACE.index("def _clear_public_search"):WORKSPACE.index("if screen_mode:")]
    assert 'st.rerun(scope="fragment")' not in search_block


def test_public_match_buttons_use_single_rerun_callbacks():
    assert "on_click=_clear_public_team_filter" in MATCHES
    assert "on_click=_show_more_public_matches" in MATCHES
    clear_block = MATCHES[MATCHES.index("def _clear_public_team_filter"):MATCHES.index("if requested_pitch_no:")]
    more_block = MATCHES[MATCHES.index("def _show_more_public_matches"):MATCHES.index('stage_timings["cards_weather_ms"]')]
    assert 'st.rerun(scope="fragment")' not in clear_block
    assert 'st.rerun(scope="fragment")' not in more_block
