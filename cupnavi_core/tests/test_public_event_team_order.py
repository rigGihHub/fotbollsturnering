from pathlib import Path

def test_public_events_follow_home_away_order():
    text=Path("app.py").read_text(encoding="utf-8")
    assert 'home_team_id = resolve_source(match_row["home_source"])' in text
    assert 'away_team_id = resolve_source(match_row["away_source"])' in text
    assert 'ordered_team_ids = [home_team_id, away_team_id]' in text

def test_event_order_is_not_alphabetical_by_team():
    text=Path("app.py").read_text(encoding="utf-8")
    start=text.index("def public_match_events_html")
    end=text.index("def render_public_view", start)
    assert "ORDER BY t.name" not in text[start:end]
