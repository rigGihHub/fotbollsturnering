import sqlite3
from cupnavi_core.product_foundation import organizer_workflow, workflow_summary, enabled_feature_groups
from cupnavi_core.schedule_quality import schedule_quality_score
from cupnavi_core.security import hash_password, verify_password, new_session_token
from cupnavi_core.observability import safe_error_record, persist_error
from cupnavi_core.migrations import apply_migrations, current_schema_version

def test_organizer_workflow_is_eight_task_based_steps():
    steps=organizer_workflow(competition_classes=1,teams=8,expected_teams=8,groups=2,pitches=2,
        rules_ready=True,matches=18,schedule_dirty=False,published=False)
    assert [s.label for s in steps] == ["Grunduppgifter","Tävlingsklasser","Lag","Grupper","Planer & tider","Regler","Schema","Publicera"]
    summary=workflow_summary(steps)
    assert summary["done"] == 7 and summary["next"].label == "Publicera"

def test_optional_features_use_progressive_disclosure():
    groups=enabled_feature_groups({"enable_team_checkin": False, "enable_fairness": True, "consider_pitch_travel": True})
    assert "fairness" in groups["optional"] and "travel_time" in groups["optional"]
    assert "checkin" not in groups["optional"]

def test_password_hash_is_salted_and_verifiable():
    encoded=hash_password("ett-mycket-bra-losenord")
    assert "ett-mycket-bra-losenord" not in encoded
    assert verify_password("ett-mycket-bra-losenord", encoded)
    assert not verify_password("fel-losenord", encoded)
    assert len(new_session_token()) >= 32

def test_schedule_quality_is_transparent_and_penalizes_hard_failures():
    good=schedule_quality_score(unscheduled=0,short_rest=0,travel_conflicts=0,late_preferences_missed=0,color_warnings=0)
    bad=schedule_quality_score(unscheduled=2,short_rest=1,travel_conflicts=1,late_preferences_missed=0,color_warnings=0)
    assert good["score"] == 100
    assert bad["score"] < good["score"]
    assert bad["penalties"]["capacity"] == 40

def test_v20_migration_adds_diagnostics_and_organization_foundation():
    con=sqlite3.connect(":memory:")
    # Minimal legacy tables needed by all historical migrations.
    con.executescript("""
      CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT);
      CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,age_class TEXT);
      CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,age_class TEXT);
      CREATE TABLE players(id INTEGER PRIMARY KEY,team_id INTEGER);
      CREATE TABLE referees(id INTEGER PRIMARY KEY,tournament_id INTEGER);
      CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,scheduled_start TEXT);
      CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER);
      CREATE TABLE feedback(id INTEGER PRIMARY KEY,tournament_id INTEGER);
      CREATE TABLE offers(id INTEGER PRIMARY KEY,tournament_id INTEGER,active INTEGER,sort_order INTEGER);
    """)
    # v20 compatibility itself must work independently on sparse schemas.
    from cupnavi_core.migrations import ensure_v20_schema_compat
    ensure_v20_schema_compat(con)
    tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"organizations","app_errors"} <= tables
    cols={r[1] for r in con.execute("PRAGMA table_info(tournaments)")}
    assert "organization_id" in cols

def test_diagnostic_record_contains_no_traceback_payload():
    con=sqlite3.connect(":memory:")
    con.execute("""CREATE TABLE app_errors(id INTEGER PRIMARY KEY,error_id TEXT,created_at TEXT,app_version TEXT,
      tournament_id INTEGER,context TEXT,error_type TEXT,message TEXT)""")
    try:
        raise ValueError("bad input")
    except Exception as exc:
        rec=safe_error_record(exc,context="public",app_version="v",tournament_id=7)
    persist_error(con,rec)
    row=con.execute("SELECT error_id,error_type,message FROM app_errors").fetchone()
    assert row[0].startswith("CN-") and row[1]=="ValueError" and row[2]=="bad input"
