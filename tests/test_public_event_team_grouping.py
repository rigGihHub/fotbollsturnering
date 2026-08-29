from pathlib import Path

def test_public_events_are_grouped_by_team():
    text=Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
    assert 'team_data.setdefault(team_id, {"name": row_value(row, "team_name", ""), "events": []})' in text
    assert "cn-event-team-name" in text
    assert "cn-event-teams" in text

def test_event_query_fetches_team_identity():
    text=Path("cupnavi_core/public_presentation_view.py").read_text(encoding="utf-8")
    assert "t.id AS team_id" in text and "t.name AS team_name" in text
