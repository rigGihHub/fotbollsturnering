from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def test_match_cards_are_compact_but_keep_mobile_layout():
    css=(ROOT/"frontend-next/src/app/public-masterpiece-v2658.css").read_text()
    assert "compact match art cards" in css
    assert "min-height:78px!important" in css
    assert "width:38px!important;height:42px!important" in css
    assert "min-height:92px!important" in css
