from pathlib import Path

def test_public_schedule_includes_match_events():
    text = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
    assert "public_match_events_html" in text
    assert "⚽" in text
    assert "🟥" in text

def test_only_goals_and_red_cards_are_selected_for_public_event_strip():
    text = Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
    assert "(s.goals > 0 OR s.red_cards > 0)" in text
    assert "Matchhändelser" in text
