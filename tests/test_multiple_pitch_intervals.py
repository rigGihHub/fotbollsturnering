import json
import sqlite3
import pytest
from cupnavi_core.pitch_availability import ensure_pitch_intervals_schema, expand_pitch_windows, write_pitch_intervals
from cupnavi_api import pitch_window_import_repository as imports
from cupnavi_api import schedule_admin_repository as schedules
from cupnavi_api.schedule_proposal import build_schedule_proposal
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



DAY = "2026-10-24"
PASSES = [{"start_time": "10:00", "end_time": "10:45"}, {"start_time": "15:15", "end_time": "19:20"}]

@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "cup.db"
    _database(path)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(imports, "_has_tournament_access", lambda account, cup: account == 7 and cup == 1)
    with sqlite3.connect(path) as con:
        con.execute("UPDATE pitch_day_windows SET confirmed=0")
        rows = [{"venue": "Plan 1", "date": DAY, **p} for p in PASSES]
        con.execute("UPDATE tournament_setup_imports SET payload_json=?", (json.dumps({"pitch_windows": rows}),))
    return path

def submit(rows=PASSES):
    return imports.commit_pitch_window_import(7, 1, [{"venue": "Plan 1", "date": DAY, **p} for p in rows])

def saved(path):
    with sqlite3.connect(path) as con:
        con.row_factory = sqlite3.Row
        return expand_pitch_windows(con.execute("SELECT * FROM pitch_day_windows").fetchall())

def test_import_reload_and_reimport_keep_both_passes_and_gap(db):
    result = submit()
    assert result["imported"] == 2
    assert result["review"]["available"] is False
    assert result["review"]["already_applied_count"] == 2
    assert [(r["start_time"], r["end_time"]) for r in saved(db)] == [("10:00", "10:45"), ("15:15", "19:20")]
    assert submit()["changed"] is False
    assert submit(PASSES[1:])["changed"] is False  # retry cannot delete morning
    with sqlite3.connect(db) as con:
        assert con.execute("SELECT schedule_dirty,is_published FROM tournaments").fetchone() == (1, 0)

def test_overlap_rejected_atomically_and_other_cup_forbidden(db):
    submit()
    before = saved(db)
    with pytest.raises(ValueError, match="överlappar"):
        submit([{"start_time": "10:30", "end_time": "16:00"}])
    assert saved(db) == before
    assert imports.commit_pitch_window_import(7, 2, []) is None

def test_additive_schema_preserves_legacy_row_and_is_repeatable(db):
    with sqlite3.connect(db) as con:
        before = con.execute("SELECT start_time,end_time,confirmed FROM pitch_day_windows").fetchone()
        ensure_pitch_intervals_schema(con)
        ensure_pitch_intervals_schema(con)
        assert con.execute("SELECT start_time,end_time,confirmed FROM pitch_day_windows").fetchone() == before
        assert con.execute("SELECT additional_windows_json FROM pitch_day_windows").fetchone() == ("[]",)

def test_proposal_uses_both_passes_and_never_closed_gap(db):
    submit()
    matches = [{"id": i, "home_source": f"team:{2*i}", "away_source": f"team:{2*i+1}", "stage": "Gruppspel"} for i in range(1, 5)]
    proposal = build_schedule_proposal(matches, {"halves": 1, "minutes_per_half": 45}, saved(db))
    starts = [p["scheduled_start"] for p in proposal["placements"]]
    assert len(starts) == 4
    assert any("10:00" in start for start in starts)
    assert any("15:15" in start for start in starts)
    assert all(start[11:16] == "10:00" or start[11:16] >= "15:15" for start in starts)

@pytest.mark.parametrize("kickoff,allowed", [("10:00", True), ("15:15", True), ("11:00", False), ("10:15", False), ("19:00", False)])
def test_schedule_confirmation_checks_entire_match_in_one_pass(db, monkeypatch, kickoff, allowed):
    submit()
    payload = {"match_count": 1, "unscheduled_count": 0, "conflict_analysis": {"error_count": 0}, "matches": [{"id": 1, "scheduled_start": f"{DAY}T{kickoff}", "pitch_number": 1}]}
    monkeypatch.setattr(schedules, "admin_schedule", lambda *_: payload)
    monkeypatch.setattr(schedules, "one", lambda *_: {"halves": 1, "minutes_per_half": 45})
    if allowed:
        assert schedules.confirm_current_schedule(7, 1) == payload
    else:
        with pytest.raises(ValueError, match="utanför"):
            schedules.confirm_current_schedule(7, 1)
