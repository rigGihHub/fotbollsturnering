from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
STATS=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")

def test_public_stats_button_updates_url_section():
    from cupnavi_core.public_view_logic import public_section_for_page
    assert public_section_for_page("Statistik") == "stats"
    assert 'st.query_params["section"] = public_section_for_page(page_value)' in APP

def test_played_match_switch_is_url_backed_and_mobile_safe():
    assert 'st.query_params["matches"] = _selected_match_view' in APP
    assert '_selected_match_view == "played"' in APP
    assert 'base_match_list = played_matches' in APP

def test_upcoming_match_parsing_is_defensive():
    start=APP.index("def _safe_public_start")
    block=APP[start:start+900]
    assert "except (TypeError, ValueError)" in block
    # v162 intentionally removed the duplicate large Next Match hero.
    matcher=APP[APP.index('if public_page == "Matcher":'):APP.index('if public_page == "Statistik":')]
    assert 'class="cn-next-match"' not in matcher

def test_public_playoff_distinguishes_configuration_errors():
    assert "Slutspelet kan inte skapas med nuvarande upplägg" in STATS
    assert "Slutspel är valt men slutspelsträdet har ännu inte skapats" in STATS

def test_admin_shows_playoff_generation_readiness():
    assert "Slutspel redo att genereras" in APP
    assert "Slutspel kan inte genereras" in APP
