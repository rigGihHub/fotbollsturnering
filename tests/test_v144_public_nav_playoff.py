from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")

def test_public_stats_button_updates_url_section():
    block=APP[APP.index("_public_section_by_page"):APP.index("public_page = st.session_state[public_page_key]")]
    assert 'st.query_params["section"] = _public_section_by_page[page_value]' in block
    assert '"Statistik": "stats"' in block

def test_played_match_switch_is_url_backed_and_mobile_safe():
    assert 'st.query_params["matches"] = _selected_match_view' in APP
    assert '_selected_match_view == "played"' in APP
    assert 'base_match_list = played_matches' in APP

def test_upcoming_match_parsing_is_defensive():
    block=APP[APP.index("def _safe_public_start"):APP.index("if upcoming_match:", APP.index("def _safe_public_start"))]
    assert "except (TypeError, ValueError)" in block

def test_public_playoff_distinguishes_configuration_errors():
    assert "Slutspelet kan inte skapas med nuvarande upplägg" in APP
    assert "Slutspel är valt men slutspelsträdet har ännu inte skapats" in APP

def test_admin_shows_playoff_generation_readiness():
    assert "Slutspel redo att genereras" in APP
    assert "Slutspel kan inte genereras" in APP
