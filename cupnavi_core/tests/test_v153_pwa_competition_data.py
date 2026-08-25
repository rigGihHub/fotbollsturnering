from pathlib import Path
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary

ROOT=Path(__file__).resolve().parents[1]
API=(ROOT/"cupnavi_api/main.py").read_text()
JS=(ROOT/"public_pwa/app.js").read_text()

def test_shared_table_engine_matches_basic_football_table():
    teams=[{"id":1,"name":"A"},{"id":2,"name":"B"},{"id":3,"name":"C"}]
    matches=[
      {"home_source":"team:1","away_source":"team:2","home_score":2,"away_score":0},
      {"home_source":"team:2","away_source":"team:3","home_score":1,"away_score":1},
    ]
    rows=calculate_group_table(teams,matches)
    assert [r["team_id"] for r in rows]==[1,3,2]
    assert rows[0]["P"]==3 and rows[1]["P"]==1

def test_h2h_tiebreak_is_supported_by_shared_engine():
    teams=[{"id":1,"name":"A"},{"id":2,"name":"B"}]
    matches=[{"home_source":"team:1","away_source":"team:2","home_score":1,"away_score":0}]
    rows=calculate_group_table(teams,matches,table_tiebreak="Inbördes möten först")
    assert rows[0]["team_id"]==1

def test_api_exposes_real_competition_endpoints():
    assert '/standings")' in API
    assert '/playoffs")' in API
    assert '/summary")' in API
    assert "calculate_group_table" in API
    assert "team_competition_summary" in API

def test_pwa_no_longer_displays_table_placeholder():
    assert "Tabellberäkning flyttas till API:t i nästa steg" not in JS
    assert "fetchStandings" in JS
    assert "fetchPlayoffs" in JS
    assert "fetchTeamSummary" in JS

def test_team_summary_returns_position_next_and_latest():
    standings={5:[{"position":2,"team_id":7,"Lag":"X"}]}
    matches=[
      {"stage":"Gruppspel","home_source":"team:7","away_source":"team:8","scheduled_start":"2026-08-24T10:00:00","home_score":2,"away_score":1},
      {"stage":"Gruppspel","home_source":"team:9","away_source":"team:7","scheduled_start":"2027-08-24T10:00:00","home_score":None,"away_score":None},
    ]
    result=team_competition_summary(7,matches,standings,5)
    assert result["group_position"]==2
    assert result["latest_result"]["home_score"]==2
    assert result["next_match"] is not None

def test_streamlit_table_uses_shared_engine():
    app=(ROOT/"app.py").read_text()
    block=app[app.index("def calculate_table"):app.index("def final_ranking_rows")]
    assert "calculate_group_table(" in block
