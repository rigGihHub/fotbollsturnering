from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_explicit_cup_is_resolved_before_public_list():
    assert "Explicit cup= must be resolved before generic public discovery" in APP
    assert "if _requested_public_row is not None:" in APP
    assert "tournaments = [_requested_public_row]" in APP

def test_explicit_cup_is_used_as_initial_seed_before_session_preference():
    from cupnavi_core.ui_logic import resolve_tournament_selector_seed
    assert resolve_tournament_selector_seed(
        [1, 2, 3], current_selection=None, requested_cup_id=2, preferred_tournament_id=3
    ) == 2

def test_switching_to_public_persists_active_cup_in_url():
    setter=APP[APP.index("def _set_view_mode"):APP.index("ADMIN_PRIMARY_FLOW")]
    assert 'st.query_params["cup"] = str(_active_cup)' in setter

def test_e2e_uses_explicit_direct_link_after_fixture():
    assert 'page.goto(f"{BASE}?cup={tid}&section=matches"' in E2E
    assert 'mobile_page.get_by_text(cup_name,exact=True).wait_for' in E2E
