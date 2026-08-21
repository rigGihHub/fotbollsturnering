from pathlib import Path

def test_public_view_has_separate_schedule_and_results_tabs():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'tr("Spelschema")' in text

def test_schedule_hides_results_and_events():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "_render_public_match_cards(schedule_matches, show_results=False)" in text
    assert 'center_text = "VS"' in text
    assert 'match_events_html = ""' in text

def test_results_only_use_played_matches_and_show_events():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "played_matches,\n            \"public_results\"" in text
    assert "_render_public_match_cards(result_matches, show_results=True)" in text
    assert "public_match_events_html(" in text and "public_events_by_match" in text

def test_both_tabs_share_group_team_pitch_filters():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'tr("Alla matcher")' in text
    assert "def _filter_public_matches(" in text
