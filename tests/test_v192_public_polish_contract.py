from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
FILTER_VIEW=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
def test_public_polish_contract():
    assert ".cn-mode-nav-safezone{height:24px!important" in APP
    assert 'with st.popover("Dela"' in APP
    start=APP.index("def _filter_public_matches")
    end=APP.index("def _render_public_match_cards",start)
    assert "render_public_match_filters_module(" in APP[start:end]
    assert 'with st.expander("Fler filter", expanded=False):' in FILTER_VIEW
    assert "PUBLIC VIEW POLISH V192" in APP
