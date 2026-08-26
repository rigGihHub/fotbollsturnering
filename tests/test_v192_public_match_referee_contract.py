from pathlib import Path

APP = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")

def test_public_match_cards_use_joined_referee_name():
    start = APP.index("def _render_public_match_cards")
    end = APP.index('if public_page == "Matcher":', start)
    block = APP[start:end]
    assert "_public_referee_label(match_row)" in block
    assert "referees.get(" not in block

def test_public_core_query_supplies_referee_name():
    assert "r.name AS referee_name" in APP
    assert "LEFT JOIN referees r ON r.id=m.referee_id" in APP
