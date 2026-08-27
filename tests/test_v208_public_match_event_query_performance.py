
from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


def test_match_events_are_loaded_after_visible_match_filtering():
    match_list_pos=APP.index("match_list, match_filter_mode, match_filter_label")
    event_pos=APP.index("visible_played_match_ids")
    assert event_pos > match_list_pos


def test_upcoming_only_view_can_skip_event_query_entirely():
    assert "if visible_played_match_ids:" in APP
    assert "WHERE s.match_id IN ({event_placeholders})" in APP


def test_event_query_is_scoped_to_visible_matches_not_whole_tournament():
    start=APP.index("# Load match events only for visible played matches")
    end=APP.index("def _safe_public_start",start)
    block=APP[start:end]
    assert "WHERE s.match_id IN ({event_placeholders})" in block
    assert "WHERE m.tournament_id=?" not in block
