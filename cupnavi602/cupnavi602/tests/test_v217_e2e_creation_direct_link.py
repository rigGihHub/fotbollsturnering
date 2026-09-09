
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_creation_defaults_to_test_for_all_environments():
    assert 'index=1' in APP[APP.index('environment_type = st.radio('):APP.index('create_locale = st.selectbox(')]

def test_canonical_cup_query_only_writes_when_value_changes():
    block=APP[APP.index("canonical_cup_query ="):APP.index("tournament = next(",APP.index("canonical_cup_query ="))]
    assert 'if str(st.query_params.get("cup", "")).strip() != canonical_cup_query:' in block
    assert 'st.query_params["cup"] = canonical_cup_query' in block

def test_public_cup_wait_targets_real_hero_and_has_diagnostics():
    assert "def wait_for_public_cup(" in E2E
    assert 'page.locator(".cup-hero .title")' in E2E
    assert "Ingen turnering är publicerad ännu." in E2E
    assert "Last body=" in E2E
