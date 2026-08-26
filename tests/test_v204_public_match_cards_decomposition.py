from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
MATCH=(ROOT/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_match_card_renderer_is_extracted():
    assert "def render_public_match_cards(" in MATCH
    assert "row_show_results = match_is_played if show_results is None" in MATCH
    assert "public_match_events_html(" in MATCH
    assert "weather_horizon = weather_now + timedelta(days=16)" in MATCH

def test_app_keeps_thin_nested_adapter():
    start=APP.index("def _render_public_match_cards")
    end=APP.index('if public_page == "Matcher":',start)
    block=APP[start:end]
    assert "render_public_match_cards_module(" in block
    assert len(block.splitlines()) < 40
