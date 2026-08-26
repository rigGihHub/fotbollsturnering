from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
INFO=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
MATCH=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_min_cup_3_has_context_and_directions():
    assert "table_position_text" in APP
    assert "Slutspel: inväntar kvalificering" in APP
    assert "Vägbeskrivning till" in APP

def test_live_center():
    assert "Cupen just nu" in APP
    assert "_live_now" in APP and "_next_matches" in APP and "_recent_results" in APP
    assert '"PÅGÅR"' in MATCH

def test_public_venue_area():
    info=INFO
    assert "venue_points_public" in info
    assert "Hitta på cupområdet" in info
    assert "Vägbeskrivning ·" in info

def test_graphical_bracket_still_present():
    assert "def render_bracket_tree" in APP
    start=APP.index("def render_bracket_tree")
    block=APP[start:start+14000]
    assert "stage_centers" in block
    assert "canvas_width" in block
    assert "stage_centers" in block
