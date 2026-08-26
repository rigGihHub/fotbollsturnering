from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_no_duplicate_view_mode_definition():
    assert APP.count("def _set_view_mode(mode):") == 1
    setter=APP[APP.index("def _set_view_mode(mode):"):APP.index("ADMIN_PRIMARY_FLOW")]
    assert 'st.query_params["cup"] = str(_active_cup)' in setter

def test_only_one_empty_state_renderer():
    assert APP.count("def render_empty_state(") == 1

def test_admin_advanced_tools_use_progressive_disclosure():
    assert '_ADMIN_PRIMARY_PAGES_BY_GROUP' in APP
    assert 'with st.expander("Fler verktyg", expanded=_advanced_active):' in APP
    assert '"Översikt": {"Adminöversikt", "Cupinställningar"}' in APP

def test_redundant_prev_next_flow_buttons_removed():
    assert "v160_prev_" not in APP
    assert "v160_next_" not in APP
    assert "Nästa rekommenderade steg" in APP

def test_database_backend_is_not_normal_user_copy():
    assert 'st.sidebar.caption("Databas: Turso"' not in APP

def test_release_v194():
    assert 'Version v.1.198' in APP
