from datetime import datetime, timedelta
from cupnavi_core.schedule_quality import assess_schedule, schedule_quality_score

def test_schedule_score_is_100_for_clean_schedule():
    rows=[
      {"scheduled_start":"2026-08-24T10:00:00","home_team_id":1,"away_team_id":2},
      {"scheduled_start":"2026-08-24T12:00:00","home_team_id":1,"away_team_id":3},
    ]
    q=assess_schedule(rows,min_rest_minutes=60)
    assert q["score"]==100
    assert q["short_rest"]==0 and q["unscheduled"]==0

def test_schedule_score_penalizes_unscheduled_and_short_rest():
    rows=[
      {"scheduled_start":"2026-08-24T10:00:00","home_team_id":1,"away_team_id":2},
      {"scheduled_start":"2026-08-24T10:30:00","home_team_id":1,"away_team_id":3},
      {"scheduled_start":None,"home_team_id":4,"away_team_id":5},
    ]
    q=assess_schedule(rows,min_rest_minutes=60)
    assert q["unscheduled"]==1
    assert q["short_rest"]==1
    assert q["score"]==75

def test_late_start_preference_is_measured_not_guessed():
    rows=[{"scheduled_start":"2026-08-24T09:00:00","home_team_id":7,"away_team_id":8}]
    q=assess_schedule(rows,late_preferences={7:"10:00"})
    assert q["late_preferences_missed"]==1
    assert q["penalties"]["preferences"]==3

def test_problem_page_renders_score_and_explains_deterministic_basis():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/"app.py").read_text()
    assert "Schedule Score" in text
    assert "Schemakvalitet" in text
    assert "det är inte en AI-sannolikhet" in text
    assert "matchplatser" in text
