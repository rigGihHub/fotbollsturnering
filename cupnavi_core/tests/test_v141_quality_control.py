import sqlite3
from datetime import datetime, timedelta
from cupnavi_core.control_center import control_center_snapshot
from cupnavi_core.system_health import system_health
from cupnavi_core.migration_contract import validate_schema_contract
from cupnavi_core.migrations import ensure_v19_schema_compat, ensure_v20_schema_compat

def test_control_center_reports_operational_state():
    now=datetime(2026,8,24,12,0)
    matches=[
      {"scheduled_start":(now+timedelta(hours=1)).isoformat(),"home_score":None,"away_score":None},
      {"scheduled_start":(now-timedelta(hours=2)).isoformat(),"home_score":None,"away_score":None},
      {"scheduled_start":(now-timedelta(hours=3)).isoformat(),"home_score":2,"away_score":1},
    ]
    s=control_center_snapshot(matches,schedule_dirty=True,now=now)
    assert s["upcoming"]==1
    assert s["missing_results"]==1
    assert s["delayed"]==1
    assert s["problems"]==2

def test_migration_contract_catches_and_then_accepts_pitch_address():
    con=sqlite3.connect(":memory:")
    con.execute("CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,PRIMARY KEY(tournament_id,pitch_number))")
    con.execute("CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY)")
    con.execute("""CREATE TABLE team_messages(id INTEGER PRIMARY KEY,tournament_id INTEGER,sender_type TEXT,
      sender_team_id INTEGER,recipient_type TEXT,recipient_team_id INTEGER,created_at TEXT,subject TEXT,message TEXT,read_at TEXT)""")
    con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY)")
    assert any("pitches" in x for x in validate_schema_contract(con))
    ensure_v19_schema_compat(con); ensure_v20_schema_compat(con)
    assert validate_schema_contract(con)==[]

def test_system_health_reads_real_schema_state():
    con=sqlite3.connect(":memory:")
    con.execute("CREATE TABLE schema_migrations(version INTEGER PRIMARY KEY,name TEXT,applied_at TEXT)")
    con.execute("INSERT INTO schema_migrations VALUES(20,'x','now')")
    con.execute("""CREATE TABLE app_errors(id INTEGER PRIMARY KEY,error_id TEXT,created_at TEXT,app_version TEXT,
      tournament_id INTEGER,context TEXT,error_type TEXT,message TEXT)""")
    h=system_health(con,app_version="v141",expected_schema=20)
    assert h["ok"] and h["schema"]==20

def test_v141_admin_contains_control_center():
    from pathlib import Path
    text=(Path(__file__).resolve().parents[1]/"app.py").read_text()
    assert "Cup Control Center" in text
    assert "Kraftigt försenade" in text
