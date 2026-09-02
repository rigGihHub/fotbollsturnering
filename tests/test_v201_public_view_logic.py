
from cupnavi_core.public_view_logic import (
    PUBLIC_PAGE_SPECS,
    public_navigation_specs,
    public_section_for_page,
    resolve_public_page,
)

def test_valid_url_section_wins_over_session_page():
    assert resolve_public_page("playoffs", "Matcher") == "Slutspel"

def test_session_page_survives_invalid_or_missing_url_section():
    assert resolve_public_page("", "Mitt lag") == "Mitt lag"
    assert resolve_public_page("unknown", "Info") == "Info"

def test_invalid_state_falls_back_to_matches():
    assert resolve_public_page("unknown", "Unknown") == "Matcher"
    assert resolve_public_page(None, None) == "Matcher"

def test_page_to_section_mapping_is_canonical():
    assert public_section_for_page("Matcher") == "matches"
    assert public_section_for_page("Tabeller") == "tables"
    assert public_section_for_page("Slutspel") == "playoffs"
    assert public_section_for_page("Mitt lag") == "team"
    assert public_section_for_page("Info") == "info"
    assert public_section_for_page("invalid") == "matches"

def test_desktop_and_mobile_navigation_share_one_source_of_truth():
    specs=public_navigation_specs()
    assert specs == PUBLIC_PAGE_SPECS
    assert len(specs) == 5
    assert [item[0] for item in specs] == ["Matcher","Mitt lag","Tabeller","Slutspel","Info"]
    assert [item[1] for item in specs] == ["matches","team","tables","playoffs","info"]
