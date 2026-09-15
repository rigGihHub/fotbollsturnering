import json
import sqlite3

import cupnavi_api.pitch_window_import_repository as repository


def _database(path):
    con = sqlite3.connect(path)
    con.executescript("""
    CREATE TABLE tournaments(id INTEGER PRIMARY KEY,start_date TEXT,end_date TEXT,tournament_date TEXT,schedule_dirty INTEGER,is_published INTEGER);
    CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT);
    CREATE TABLE pitch_day_windows(tournament_id INTEGER,pitch_number INTEGER,play_date TEXT,start_time TEXT,end_time TEXT,confirmed INTEGER,UNIQUE(tournament_id,pitch_number,play_date));
    CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,scheduled_start TEXT);
    CREATE TABLE tournament_setup_imports(id INTEGER PRIMARY KEY,tournament_id INTEGER,import_kind TEXT,payload_json TEXT,source_name TEXT);
    """)
    con.execute("INSERT INTO tournaments VALUES(1,'2026-10-24','2026-10-24',NULL,0,1)")
    con.execute("INSERT INTO pitches VALUES(1,1,'Plan 1')")
    con.execute("INSERT INTO pitch_day_windows VALUES(1,1,'2026-10-24','09:00','18:00',1)")
    con.execute("INSERT INTO matches VALUES(1,1,'2026-10-24T09:00:00')")
    con.execute("INSERT INTO tournament_setup_imports VALUES(1,1,'initial_setup',?, 'foto.png')", (json.dumps({"pitch_windows":[{"venue":"Sörbyvallen","date":"2026-10-24","start_time":"09:00","end_time":"18:00"}]}),))
    con.commit(); con.close()


def test_confirmed_values_remain_applied_after_pitch_was_renamed(monkeypatch, tmp_path):
    db = tmp_path / "cup.db"; _database(db)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(db))
    monkeypatch.setattr(repository, "_has_tournament_access", lambda *_: True)
    review = repository.pitch_window_import_review(7, 1)
    assert review["available"] is False
    assert review["already_applied_count"] == 1


def test_resaving_identical_window_does_not_dirty_or_unpublish(monkeypatch, tmp_path):
    db = tmp_path / "cup.db"; _database(db)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(db))
    monkeypatch.setattr(repository, "_has_tournament_access", lambda *_: True)
    result = repository.commit_pitch_window_import(7, 1, [{"venue":"Plan 1","date":"2026-10-24","start_time":"09:00","end_time":"18:00"}])
    assert result["changed"] is False
    con = sqlite3.connect(db)
    assert con.execute("SELECT schedule_dirty,is_published FROM tournaments WHERE id=1").fetchone() == (0, 1)
