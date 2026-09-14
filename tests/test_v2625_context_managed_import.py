import sqlite3
from contextlib import contextmanager
from datetime import date

from cupnavi_api.initial_import_idempotency import apply_document_matches_idempotent
from cupnavi_core.cup_document_creator_view import save_setup_import_snapshot


def _database(tmp_path):
    path = tmp_path / "managed-import.db"
    connection = sqlite3.connect(path)
    connection.executescript("""
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,schedule_dirty INTEGER DEFAULT 1,is_published INTEGER DEFAULT 0);
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,group_id INTEGER);
        CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,PRIMARY KEY(tournament_id,pitch_number));
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,stage TEXT,match_no INTEGER,home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,schedule_locked INTEGER DEFAULT 0);
        CREATE TABLE tournament_setup_imports(id INTEGER PRIMARY KEY,tournament_id INTEGER,import_kind TEXT,source_name TEXT,payload_json TEXT);
        INSERT INTO tournaments(id) VALUES(1);
        INSERT INTO groups VALUES(10,1,'A');
        INSERT INTO teams VALUES(20,1,'ÖSK',10);
        INSERT INTO teams VALUES(21,1,'AIK',10);
    """)
    connection.commit()
    connection.close()

    @contextmanager
    def factory():
        managed = sqlite3.connect(path)
        try:
            yield managed
        finally:
            managed.close()

    return path, factory


def test_initial_import_accepts_api_context_manager_factory(tmp_path):
    path, factory = _database(tmp_path)
    proposal = {"source_name": "test.pdf", "matches": [{
        "time": "09:30", "venue": "Plan 1", "group_name": "A",
        "home_team": "ÖSK", "away_team": "AIK",
    }]}

    created, replay = apply_document_matches_idempotent(factory, 1, proposal, date(2026, 9, 12))
    assert (created, replay) == (1, False)
    assert apply_document_matches_idempotent(factory, 1, proposal, date(2026, 9, 12)) == (0, True)
    assert save_setup_import_snapshot(factory, 1, proposal) is not None

    connection = sqlite3.connect(path)
    assert connection.execute("SELECT COUNT(*) FROM matches").fetchone()[0] == 1
    assert connection.execute("SELECT COUNT(*) FROM tournament_setup_imports").fetchone()[0] == 1
    connection.close()
