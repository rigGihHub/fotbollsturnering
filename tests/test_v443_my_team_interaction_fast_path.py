from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
TEAM = (ROOT / "cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
MATCHES = (ROOT / "cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")


def test_v443_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"


def test_my_team_selection_and_actions_use_single_rerun_callbacks():
    assert "on_change=_sync_public_favorite_team" in TEAM
    assert "on_click=_open_public_team_matches" in TEAM
    assert "on_click=_clear_public_favorite_team" in TEAM
    action_block = TEAM[TEAM.index("def _sync_public_favorite_team"):TEAM.index("if favorite_next:")]
    assert 'st.rerun(scope="fragment")' not in action_block


def test_pre_result_matches_skip_empty_scorer_overview_roundtrip():
    assert 'and bool(played_matches)' in MATCHES
    assert 'if scorer_enabled else {"leader_rows": []}' in MATCHES
