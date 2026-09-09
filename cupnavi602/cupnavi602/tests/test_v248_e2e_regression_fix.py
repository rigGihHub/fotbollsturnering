
from pathlib import Path
E2E=(Path(__file__).resolve().parents[1]/"e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_lifecycle_opens_collapsed_test_tools_before_demo_button():
    lifecycle=E2E[E2E.index("def test_full_cup_lifecycle_journey"):E2E.index("def test_active_tournament_switch")]
    assert 'page.locator("details").filter(has_text="Testverktyg").first' in lifecycle
    assert 'test_tools.locator("summary").first.click(force=True)' in lifecycle
    assert 'demo_button=test_tools.get_by_role("button",name=re.compile(r"^Skapa testdata:"))' in lifecycle

def test_selectbox_helper_has_cross_browser_popup_fallback():
    helper=E2E[E2E.index("def choose_streamlit_option"):E2E.index("def _cup_progress_state")]
    assert 'get_by_role("option",name=option,exact=True)' in helper
    assert "'[role=\"listbox\"], [data-baseweb=\"popover\"], [data-baseweb=\"menu\"]'" in helper
    assert "popup_text=page.locator" in helper and ".get_by_text(option,exact=True)" in helper
    assert "combo.input_value().strip() == option" in helper
