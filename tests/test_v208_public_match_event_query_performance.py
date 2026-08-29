
from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
VIEW=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_matches_view.py").read_text(encoding="utf-8")
REPO=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_repository.py").read_text(encoding="utf-8")


def test_match_events_are_loaded_after_visible_match_filtering():
    match_list_pos=VIEW.index("match_list, _match_filter_mode, match_filter_label")
    event_pos=VIEW.index("visible_played_match_ids")
    assert event_pos > match_list_pos


def test_upcoming_only_view_can_skip_event_query_entirely():
    assert "if visible_played_match_ids else {}" in VIEW
    assert "WHERE s.match_id IN ({placeholders})" in REPO


def test_event_query_is_scoped_to_visible_matches_not_whole_tournament():
    start=REPO.index("def fetch_public_match_events")
    block=REPO[start:]
    assert "WHERE s.match_id IN ({placeholders})" in block
    assert "WHERE m.tournament_id=?" not in block
