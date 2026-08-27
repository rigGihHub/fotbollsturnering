
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def _helper():
    return E2E[
        E2E.index("def create_test_tournament_through_ui"):
        E2E.index("def representative_public_tokens")
    ]

def test_visible_streamlit_radio_label_is_used():
    helper=_helper()
    assert 'create_form.locator(\'[data-testid="stRadio"]\').first' in helper
    assert 'locator("label").filter(has_text="Testmiljö")' in helper
    assert "test_environment_label.click(force=True)" in helper

def test_hidden_radio_input_is_not_checked_directly():
    assert ".check(force=True)" not in _helper()

def test_radio_state_is_reacquired_and_verified():
    helper=_helper()
    assert 'get_by_role("radio",name="Testmiljö",exact=True)' in helper
    assert "test_environment.wait_for(state=\"attached\"" in helper
    assert "test_environment.is_checked()" in helper
