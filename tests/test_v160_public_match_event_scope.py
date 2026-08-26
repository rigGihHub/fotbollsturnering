from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
MATCH=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_public_match_cards_receive_event_map_explicitly():
    block=MATCH
    assert "events_by_match=None" in block
    assert "events_by_match = events_by_match or {}" in block
    assert 'rows=events_by_match.get(match_row["id"], [])' in block
    assert 'rows=public_events_by_match.get(match_row["id"], [])' not in block

def test_match_fragment_passes_its_local_event_map():
    start=APP.index('if public_page == "Matcher":')
    end=APP.index('if public_page == "Statistik":', start)
    block=APP[start:end]
    assert "events_by_match=public_events_by_match" in block
