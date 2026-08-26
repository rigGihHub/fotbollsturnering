from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
MATCH = (Path(__file__).resolve().parents[1] / "cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_public_match_cards_use_joined_referee_name():
    block = MATCH
    assert "public_referee_label(match_row)" in block
    assert "referees.get(" not in block

def test_public_core_query_supplies_referee_name():
    assert "r.name AS referee_name" in APP
    assert "LEFT JOIN referees r ON r.id=m.referee_id" in APP
