import sqlite3
from pathlib import Path
import cupnavi_api.repository as repo

def test_standings_inputs_batches_by_group(monkeypatch,tmp_path):
    db=tmp_path/"x.db"
    con=sqlite3.connect(db)
    con.executescript("""
    CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,age_class TEXT);
    CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,group_id INTEGER);
    CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,stage TEXT,home_source TEXT,away_source TEXT,home_score INTEGER,away_score INTEGER);
    INSERT INTO groups VALUES(1,7,'A',NULL),(2,7,'B',NULL);
    INSERT INTO teams VALUES(10,7,'A1',1),(11,7,'A2',1),(20,7,'B1',2),(21,7,'B2',2);
    INSERT INTO matches VALUES(30,7,1,'Gruppspel','team:10','team:11',1,0),
                              (31,7,2,'Gruppspel','team:20','team:21',2,2);
    """)
    con.commit(); con.close()
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH",str(db))
    monkeypatch.delenv("TURSO_DATABASE_URL",raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN",raising=False)
    groups,teams,matches=repo.standings_inputs(7)
    assert len(groups)==2
    assert len(teams[1])==2 and len(teams[2])==2
    assert len(matches[1])==1 and len(matches[2])==1
