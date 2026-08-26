
from pathlib import Path
APP = Path(__file__).resolve().parents[1] / "app.py"

def test_selector_is_not_reset_from_preferred_or_url_every_rerun():
    text = APP.read_text(encoding="utf-8")
    assert 'if st.session_state.get("active_tournament_selector") not in tournament_ids:' in text
    assert 'st.session_state["preferred_tournament_id"] = int(tid)' in text
    block = text[text.index("# Seed the widget only"):text.index("tournament = next(t for t in tournaments if t[\"id\"] == tid)")]
    assert 'st.session_state["active_tournament_selector"] = requested_cup_id' not in block
    assert 'st.session_state["active_tournament_selector"] = preferred_tournament_id' not in block
