from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")


def _overview_block():
    start = APP.index('elif admin_page == "Adminöversikt":')
    end = APP.index('if admin_page == "Kontroller":', start)
    return APP[start:end]


def test_fairness_query_is_lazy_on_admin_overview():
    block = _overview_block()
    assert 'fairness_requested = bool(st.session_state.get(fairness_state_key, False))' in block
    assert 'if fairness_requested or control_center_enabled:' in block
    assert 'Kör fairnessanalys' in block


def test_control_center_shares_lazy_match_snapshot():
    block = _overview_block()
    assert 'control_matches = fairness_matches or []' in block
    assert block.count('SELECT * FROM matches WHERE tournament_id=? AND scheduled_start IS NOT NULL') == 1


def test_release_version_305():
    assert '2026.08.31-347-SCHEDULE-READINESS-POLISH' in APP
