from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_schedule_and_results_are_merged_into_matches():
    text = app_text()
    view = Path('cupnavi_core/public_matches_view.py').read_text(encoding='utf-8')
    assert 'if public_page == "Matcher":' in text
    assert 'tr("Kommande")' in view
    assert 'tr("Spelade")' in view
    assert 'show_results=None' in view

def test_played_matches_show_events_in_combined_match_cards():
    text = Path("cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")
    assert "row_show_results = match_is_played if show_results is None" in text
    assert "public_match_events_html(" in text
