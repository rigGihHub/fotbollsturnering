import sqlite3
from cupnavi_core.backup import build_backup_bytes, validate_backup_bytes, restore_backup_as_new_tournament

def test_restore_creates_new_cup_and_remaps_team_group_match():
    con=sqlite3.connect(":memory:")
    con.execute("PRAGMA foreign_keys=ON")
    con.executescript("""
    CREATE TABLE tournaments(id INTEGER PRIMARY KEY AUTOINCREMENT,name TEXT,environment_type TEXT,is_published INTEGER,lifecycle_status TEXT,public_slug TEXT,completed_at TEXT,trashed_at TEXT);
    CREATE TABLE competition_classes(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT);
    CREATE TABLE groups(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT);
    CREATE TABLE teams(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT,group_id INTEGER);
    CREATE TABLE players(id INTEGER PRIMARY KEY AUTOINCREMENT,team_id INTEGER,name TEXT);
    CREATE TABLE referees(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT);
    CREATE TABLE brackets(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,name TEXT,size INTEGER,bronze_match INTEGER);
    CREATE TABLE matches(id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,stage TEXT,round_no INTEGER,match_no INTEGER,home_source TEXT,away_source TEXT,home_score INTEGER,away_score INTEGER,home_penalties INTEGER,away_penalties INTEGER,referee_id INTEGER,schedule_published INTEGER,schedule_locked INTEGER,decided_winner_id INTEGER);
    CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY);
    """)
    datasets={
      "tournaments":[{"id":7,"name":"Original","environment_type":"production","is_published":1,"lifecycle_status":"live"}],
      "groups":[{"id":10,"tournament_id":7,"name":"A"}],
      "teams":[{"id":20,"tournament_id":7,"name":"Lag A","group_id":10},{"id":21,"tournament_id":7,"name":"Lag B","group_id":10}],
      "matches":[{"id":30,"tournament_id":7,"group_id":10,"bracket_id":None,"stage":"Gruppspel","round_no":1,"match_no":1,"home_source":"team:20","away_source":"team:21","home_score":2,"away_score":1,"referee_id":None,"schedule_published":1,"schedule_locked":0,"decided_winner_id":None}],
    }
    raw,_=build_backup_bytes("x",7,datasets)
    payload=validate_backup_bytes(raw)
    new_id=restore_backup_as_new_tournament(con,payload,name="Återställd",environment_type="test")
    assert new_id != 7
    restored=con.execute("SELECT name,environment_type,is_published,lifecycle_status FROM tournaments WHERE id=?",(new_id,)).fetchone()
    assert restored==("Återställd","test",0,"draft")
    teams=con.execute("SELECT id,name,group_id FROM teams WHERE tournament_id=? ORDER BY name",(new_id,)).fetchall()
    match=con.execute("SELECT home_source,away_source,home_score,away_score FROM matches WHERE tournament_id=?",(new_id,)).fetchone()
    assert match[0] == f"team:{teams[0][0]}"
    assert match[1] == f"team:{teams[1][0]}"
    assert match[2:] == (2,1)
