from pathlib import Path

def test_public_events_are_grouped_by_team():
    text=Path("app.py").read_text(encoding="utf-8")
    assert 'grouped.setdefault(row["team_name"], [])' in text
    assert "cn-event-team-name" in text
    assert "cn-event-teams" in text

def test_event_query_fetches_team_identity():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "t.id AS team_id, t.name AS team_name" in text
