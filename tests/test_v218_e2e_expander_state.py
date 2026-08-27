
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
E2E=(ROOT/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")


def test_creation_helper_ensures_expander_open_instead_of_toggling_title():
    assert "def _ensure_create_tournament_expander_open(page):" in E2E
    helper=E2E[
        E2E.index("def create_test_tournament_through_ui"):
        E2E.index("def representative_public_tokens")
    ]
    assert "create_form=_ensure_create_tournament_expander_open(page)" in helper
    assert 'page.get_by_text("Skapa ny turnering",exact=True).click()' not in helper


def test_expander_state_is_checked_before_clicking_summary():
    block=E2E[
        E2E.index("def _ensure_create_tournament_expander_open"):
        E2E.index("def create_test_tournament_through_ui")
    ]
    assert 'if expander.get_attribute("open") is None:' in block
    assert 'expander.locator("summary").first' in block
    assert "Create tournament expander did not open" in block


def test_submit_is_scoped_to_visible_verified_form():
    helper=E2E[
        E2E.index("def create_test_tournament_through_ui"):
        E2E.index("def representative_public_tokens")
    ]
    assert 'create_form.get_by_role("button",name="Skapa",exact=True)' in helper
    assert 'submit.wait_for(state="visible",timeout=10000)' in helper
    assert "submit.click(force=True)" in helper
