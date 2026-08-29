from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
INFO=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
MATCH=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
FOLLOW=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_team_follow.py").read_text(encoding="utf-8")
FOLLOW_VIEW=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
FEED=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_feed_logic.py").read_text(encoding="utf-8")
MATCHES=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
PRESENTATION=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")

def test_min_cup_3_has_context_and_directions():
    assert "table_position_text" in FOLLOW_VIEW
    assert "Slutspel: inväntar kvalificering" in FOLLOW
    assert "Vägbeskrivning till" in FOLLOW_VIEW

def test_live_center():
    assert "Cupen just nu" in FEED
    assert "live_now" in MATCHES and "next_matches" in MATCHES and "recent_results" in MATCHES
    assert '"PÅGÅR"' in MATCH

def test_public_venue_area():
    info=INFO
    assert "venue_points_public" in info
    assert "Hitta på cupområdet" in info
    assert "Vägbeskrivning ·" in info

def test_graphical_bracket_still_present():
    assert "def render_bracket_tree" in PRESENTATION
    start=PRESENTATION.index("def render_bracket_tree")
    block=PRESENTATION[start:start+14000]
    assert "stage_centers" in block
    assert "canvas_width" in block
    assert "stage_centers" in block
