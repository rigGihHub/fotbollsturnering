from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_mode_preselects_test_environment_in_real_form():
    assert 'index=1' in APP[APP.index('environment_type = st.radio('):APP.index('create_locale = st.selectbox(')]

def test_e2e_helper_verifies_radio_without_driving_hidden_control():
    helper=E2E[
        E2E.index("def create_test_tournament_through_ui"):
        E2E.index("def representative_public_tokens")
    ]
    assert 'get_by_role("radio",name="Testmiljö",exact=True)' in helper
    assert "test_environment.is_checked()" in helper
    assert ".check(force=True)" not in helper
    assert "test_environment_label.click" not in helper
