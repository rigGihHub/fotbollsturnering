import sqlite3

import pytest

from cupnavi_api.playoff_admin_repository import admin_playoffs, update_playoff_settings
from cupnavi_api.referee_admin_repository import (
    admin_referees,
    assign_referee,
    create_referee,
    delete_referee,
)
from cupnavi_api.main import app


def _schema(path):
    con=sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE tournament_members(organizer_account_id INTEGER NOT NULL,tournament_id INTEGER NOT NULL);
        CREATE TABLE tournaments(
            id INTEGER PRIMARY KEY,playoff_format TEXT DEFAULT 'Inget slutspel',bronze_match INTEGER DEFAULT 0,
            playoff_tie_rule TEXT DEFAULT 'Straffar direkt',playoff_extra_time_minutes INTEGER DEFAULT 0,
            schedule_dirty INTEGER DEFAULT 0,is_published INTEGER DEFAULT 1
        );
        CREATE TABLE referees(
            id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,name TEXT NOT NULL,
            email TEXT,phone TEXT,notes TEXT,active INTEGER DEFAULT 1
        );
        CREATE TABLE referee_acknowledgements(
            id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,referee_id INTEGER NOT NULL,
            match_id INTEGER NOT NULL,acknowledged_at TEXT NOT NULL
        );
        CREATE TABLE brackets(
            id INTEGER PRIMARY KEY AUTOINCREMENT,tournament_id INTEGER NOT NULL,name TEXT NOT NULL,size INTEGER NOT NULL,
            bronze_match INTEGER DEFAULT 0
        );
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,tournament_id INTEGER NOT NULL,bracket_id INTEGER,stage TEXT,round_no INTEGER,match_no INTEGER,
            home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,home_score INTEGER,away_score INTEGER,
            home_penalties INTEGER,away_penalties INTEGER,decided_winner_id INTEGER,schedule_locked INTEGER DEFAULT 0,
            schedule_published INTEGER DEFAULT 1,referee_id INTEGER
        );
        INSERT INTO tournament_members VALUES(1,10);
        INSERT INTO tournaments(id) VALUES(10);
        INSERT INTO matches(id,tournament_id,stage,match_no,home_source,away_source) VALUES(1,10,'Gruppspel',1,'team:1','team:2');
        """
    )
    con.commit();con.close()


def _env(monkeypatch,path):
    monkeypatch.delenv('TURSO_DATABASE_URL',raising=False)
    monkeypatch.delenv('TURSO_AUTH_TOKEN',raising=False)
    monkeypatch.setenv('CUPNAVI_API_SQLITE_PATH',str(path))


def test_referee_crud_assignment_and_delete_protection(monkeypatch,tmp_path):
    db=tmp_path/'v634.sqlite';_schema(db);_env(monkeypatch,db)
    referee=create_referee(1,10,{'name':'Anna Domare','email':'anna@example.se'})
    assert referee['name']=='Anna Domare'
    assigned=assign_referee(1,10,1,referee['id'])
    assert assigned['matches'][0]['referee_id']==referee['id']
    assert assigned['referees'][0]['assignment_count']==1
    with pytest.raises(ValueError,match='tilldelad matcher'):
        delete_referee(1,10,referee['id'])
    assign_referee(1,10,1,None)
    deleted=delete_referee(1,10,referee['id'])
    assert deleted['name']=='Anna Domare'


def test_referee_schema_introspection_disables_assignment_when_column_missing(monkeypatch,tmp_path):
    db=tmp_path/'v634-ref-no-assignment.sqlite';_schema(db)
    con=sqlite3.connect(db)
    con.execute('ALTER TABLE matches RENAME TO matches_old')
    con.execute('CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,stage TEXT,home_score INTEGER,away_score INTEGER)')
    con.execute("INSERT INTO matches(id,tournament_id,stage) VALUES(1,10,'Gruppspel')")
    con.commit();con.close();_env(monkeypatch,db)
    payload=admin_referees(1,10)
    assert payload['available'] is True
    assert payload['supports_assignment'] is False


def test_playoff_structure_change_blocked_when_bracket_exists(monkeypatch,tmp_path):
    db=tmp_path/'v634-playoff.sqlite';_schema(db);_env(monkeypatch,db)
    con=sqlite3.connect(db)
    con.execute("INSERT INTO brackets(tournament_id,name,size,bronze_match) VALUES(10,'A-slutspel',4,0)")
    bracket_id=con.execute('SELECT id FROM brackets WHERE tournament_id=10').fetchone()[0]
    con.execute("INSERT INTO matches(id,tournament_id,bracket_id,stage,round_no,match_no,home_source,away_source) VALUES(2,10,?,'Semifinal',1,1,'group:1:1','group:2:2')",(bracket_id,))
    con.commit();con.close()
    payload=admin_playoffs(1,10)
    assert payload['structure_locked'] is True
    with pytest.raises(ValueError,match='strukturen'):
        update_playoff_settings(1,10,{'playoff_format':'A- och B-slutspel'})


def test_playoff_settings_unpublish_when_safe(monkeypatch,tmp_path):
    db=tmp_path/'v634-playoff-settings.sqlite';_schema(db);_env(monkeypatch,db)
    saved=update_playoff_settings(1,10,{
        'playoff_format':'Slutspel – bara ettor och tvåor','bronze_match':True,
        'playoff_tie_rule':'Förlängning + straffar','playoff_extra_time_minutes':10,
    })
    assert saved['playoff_format']=='Slutspel – bara ettor och tvåor'
    assert saved['bronze_match'] is True
    con=sqlite3.connect(db);state=con.execute('SELECT schedule_dirty,is_published FROM tournaments WHERE id=10').fetchone();con.close()
    assert state==(1,0)


def test_v634_routes_exposed():
    routes={(route.path,method) for route in app.routes for method in getattr(route,'methods',set())}
    assert ('/api/admin/cups/{tournament_id}/referees','GET') in routes
    assert ('/api/admin/cups/{tournament_id}/referees','POST') in routes
    assert ('/api/admin/cups/{tournament_id}/referees/{referee_id}','PUT') in routes
    assert ('/api/admin/cups/{tournament_id}/referees/matches/{match_id}','PUT') in routes
    assert ('/api/admin/cups/{tournament_id}/playoffs','GET') in routes
    assert ('/api/admin/cups/{tournament_id}/playoffs','PUT') in routes
