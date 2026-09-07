import sqlite3
from datetime import date
import pytest
from cupnavi_core.cup_document_creator_view import apply_document_matches


def make_db(tmp_path):
    path=tmp_path/'x.db'; con=sqlite3.connect(path)
    con.executescript('''
    CREATE TABLE tournaments(id INTEGER PRIMARY KEY,schedule_dirty INTEGER DEFAULT 1,is_published INTEGER DEFAULT 0);
    CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
    CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,group_id INTEGER);
    CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,PRIMARY KEY(tournament_id,pitch_number));
    CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,stage TEXT,match_no INTEGER,home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,schedule_locked INTEGER DEFAULT 0);
    INSERT INTO tournaments(id) VALUES(1); INSERT INTO groups VALUES(10,1,'A');
    INSERT INTO teams VALUES(20,1,'ÖSK',10); INSERT INTO teams VALUES(21,1,'AIK',10);
    '''); con.commit(); con.close()
    return path, lambda: sqlite3.connect(path)


def test_imported_schedule_is_explicit_locked_and_preserved(tmp_path):
    path, factory=make_db(tmp_path)
    prefill={'matches':[{'time':'09:30','venue':'Plan 1','group_name':'A','home_team':'ÖSK','away_team':'AIK'}]}
    assert apply_document_matches(factory,1,prefill,date(2026,9,12)) == 1
    con=sqlite3.connect(path)
    row=con.execute('SELECT scheduled_start,pitch_number,schedule_locked FROM matches').fetchone()
    assert row == ('2026-09-12T09:30',1,1)
    with pytest.raises(ValueError, match='redan ett schema'):
        apply_document_matches(factory,1,prefill,date(2026,9,12))
    assert con.execute('SELECT COUNT(*) FROM matches').fetchone()[0] == 1


def test_bad_team_rolls_back_pitch_and_matches(tmp_path):
    path, factory=make_db(tmp_path)
    prefill={'matches':[{'time':'09:30','venue':'Plan 1','group_name':'A','home_team':'ÖSK','away_team':'Saknas'}]}
    with pytest.raises(ValueError): apply_document_matches(factory,1,prefill,date(2026,9,12))
    con=sqlite3.connect(path)
    assert con.execute('SELECT COUNT(*) FROM matches').fetchone()[0] == 0
    assert con.execute('SELECT COUNT(*) FROM pitches').fetchone()[0] == 0
