from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
FILTER_VIEW=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_filters_view.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
def test_public_polish_contract():
    assert ".cn-mode-nav-safezone{height:24px!important" in STYLE
    assert 'with st.popover("Dela"' in APP
    start=WORKSPACE.index("def _filter_public_matches")
    end=WORKSPACE.index("def _render_public_match_cards",start)
    assert "render_public_match_filters_module(" in WORKSPACE[start:end]
    assert 'with st.expander("Filter & visning", expanded=False):' in FILTER_VIEW
    assert "PUBLIC VIEW POLISH V192" in APP
