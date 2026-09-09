from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
FEED=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_feed_logic.py").read_text(encoding="utf-8")
STYLE=(Path(__file__).resolve().parents[1]/"cupnavi_core/style_system.py").read_text(encoding="utf-8")

def test_live_center_uses_visual_cards():
    assert "cn-live-grid" in STYLE
    assert "cn-live-card" in STYLE
    assert "cn-live-head" in STYLE
    assert "Nästa matcher i turneringen." in FEED

def test_live_center_is_responsive():
    assert "@media(max-width:900px){" in STYLE
    assert ".cn-live-grid{grid-template-columns:1fr}" in STYLE

def test_public_cup_feed_is_removed():
    public=APP[APP.index("def render_public_view"):APP.index("def render_match_reporter_view")]
    assert 'st.expander("📣 Cupflöde"' not in public
    assert "SELECT * FROM cup_feed WHERE tournament_id=? AND public=1" not in public

def test_cup_tools_no_longer_show_feed_tab():
    tools=APP[APP.index('if admin_page == "Cupverktyg":'):APP.index('if admin_page == "Tabeller":')]
    assert '"Cupflöde"' not in tools
    assert "Publikt cupflöde" not in tools
    assert "Publicera i cupflödet" not in tools
    assert 'with tool_tabs[6]:' in tools
    assert "Automatisk cupsummering" in tools

def test_feed_storage_remains_for_compatibility_history():
    assert "def add_feed_item" in APP
    assert '"cup_feed": [dict(row)' in APP
