import sqlite3

import cupnavi_api.publish_reporting_repository as publication
import cupnavi_api.repository as repository


SCHEMA = """
CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT,public_slug TEXT,is_published INTEGER DEFAULT 0,schedule_dirty INTEGER DEFAULT 0);
CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,scheduled_start TEXT,pitch_number INTEGER,schedule_published INTEGER DEFAULT 0);
"""


def test_publishing_exposes_every_scheduled_match_atomically(monkeypatch, tmp_path):
    db = tmp_path / "cup.db"
    con = sqlite3.connect(db)
    con.executescript(SCHEMA)
    con.execute("INSERT INTO tournaments VALUES(1,'Cup','cup',0,0)")
    con.executemany("INSERT INTO matches VALUES(?,?,?,?,?)", [(1,1,'2026-10-24T09:00:00',1,0),(2,1,None,None,0)])
    con.commit(); con.close()
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(db))
    monkeypatch.setattr(publication, "_has_tournament_access", lambda *_: True)
    monkeypatch.setattr(publication, "_publication_payload", lambda _id: {"blockers": [], "ready": True})
    publication.set_publication(7, 1, True)
    con = sqlite3.connect(db)
    assert con.execute("SELECT is_published FROM tournaments WHERE id=1").fetchone()[0] == 1
    assert con.execute("SELECT schedule_published FROM matches WHERE id=1").fetchone()[0] == 1
    assert con.execute("SELECT schedule_published FROM matches WHERE id=2").fetchone()[0] == 0


def test_draft_preview_does_not_apply_public_match_filter():
    source = repository.public_snapshot.__code__.co_consts
    text = " ".join(value for value in source if isinstance(value, str))
    assert 'match_publish_filter' not in text  # implementation is local code, asserted below from source file
    module_text = open(repository.__file__, encoding="utf-8").read()
    assert 'match_publish_filter="" if include_unpublished else " AND schedule_published=1"' in module_text
