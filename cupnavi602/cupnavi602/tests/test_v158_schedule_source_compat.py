from pathlib import Path
from cupnavi_core.schedule_quality import assess_schedule

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def test_problem_solutions_uses_modern_match_source_columns():
    assert "SELECT scheduled_start,home_source,away_source FROM matches WHERE tournament_id=?" in APP
    assert "SELECT scheduled_start,home_team_id,away_team_id FROM matches WHERE tournament_id=?" not in APP

def test_schedule_quality_accepts_team_sources():
    rows=[
      {"scheduled_start":"2026-08-24T10:00:00","home_source":"team:1","away_source":"team:2"},
      {"scheduled_start":"2026-08-24T10:30:00","home_source":"team:1","away_source":"team:3"},
    ]
    q=assess_schedule(rows,min_rest_minutes=60)
    assert q["short_rest"]==1

def test_schedule_quality_ignores_unresolved_playoff_sources():
    rows=[
      {"scheduled_start":"2026-08-24T12:00:00","home_source":"group:1:1","away_source":"winner:5"},
    ]
    q=assess_schedule(rows,min_rest_minutes=60)
    assert q["short_rest"]==0
    assert q["unscheduled"]==0

def test_no_matches_sql_reads_removed_team_id_columns():
    import re
    sql_strings=re.findall(r'["\']SELECT[^"\']+["\']',APP,re.I)
    offenders=[s for s in sql_strings if "FROM matches" in s and ("home_team_id" in s or "away_team_id" in s)]
    assert offenders==[]
