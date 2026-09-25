from pathlib import Path

from cupnavi_core.public_competition import calculate_group_table

ROOT=Path(__file__).resolve().parents[1]
REPORTING=(ROOT/"cupnavi_api/publish_reporting_repository.py").read_text(encoding="utf-8")

def test_group_table_points_goal_difference_and_order():
    teams=[{"id":1,"name":"AIK"},{"id":2,"name":"Hammarby"},{"id":3,"name":"Örebro SK"}]
    matches=[
        {"home_source":"team:1","away_source":"team:2","home_score":2,"away_score":1},
        {"home_source":"team:3","away_source":"team:1","home_score":1,"away_score":1},
        {"home_source":"team:2","away_source":"team:3","home_score":0,"away_score":3},
    ]
    rows=calculate_group_table(teams,matches,points_win=3,points_draw=1,points_loss=0)
    by_name={row["Lag"]:row for row in rows}
    assert by_name["Örebro SK"]["P"]==4 and by_name["Örebro SK"]["MS"]==3
    assert by_name["AIK"]["P"]==4 and by_name["AIK"]["MS"]==1
    assert by_name["Hammarby"]["P"]==0 and by_name["Hammarby"]["MS"]==-4
    assert [row["Lag"] for row in rows]==["Örebro SK","AIK","Hammarby"]

def test_unplayed_matches_never_affect_table():
    teams=[{"id":1,"name":"A"},{"id":2,"name":"B"}]
    rows=calculate_group_table(teams,[{"home_source":"team:1","away_source":"team:2","home_score":None,"away_score":None}])
    assert all(row["S"]==0 and row["P"]==0 and row["MS"]==0 for row in rows)

def test_result_save_has_optimistic_concurrency_guard():
    assert 'row.get("home_score") != expected_home' in REPORTING
    assert 'row.get("away_score") != expected_away' in REPORTING
    assert "Resultatet har ändrats av någon annan" in REPORTING

def test_result_save_is_scoped_to_match_and_tournament():
    assert 'SELECT * FROM matches WHERE id=? AND tournament_id=?' in REPORTING
    assert 'WHERE id=? AND tournament_id=?' in REPORTING

def test_playoff_dependency_change_is_blocked_when_downstream_is_locked():
    assert "transitive_downstream_match_ids" in REPORTING
    assert "dependency_impact(" in REPORTING
    assert "if impact.blocked:" in REPORTING

def test_admin_reset_clears_result_lifecycle_and_events_with_concurrency_guard():
    assert "def reset_result(" in REPORTING
    assert "new_winner_side=None" in REPORTING
    assert "SET home_score=NULL,away_score=NULL" in REPORTING
    assert "match_status=?" in REPORTING
    assert 'DELETE FROM player_match_stats WHERE match_id=?' in REPORTING
    assert 'DELETE FROM match_goal_minutes WHERE match_id=?' in REPORTING
    assert "Resultatet eller matchstatusen har ändrats av någon annan" in REPORTING
