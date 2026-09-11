import sqlite3

import pytest

from cupnavi_api.rules_admin_repository import admin_rules, update_rules
from cupnavi_api.schedule_admin_repository import admin_schedule, update_match_schedule
from cupnavi_api.main import app


def _schema(path):
    con=sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE tournament_members(organizer_account_id INTEGER NOT NULL,tournament_id INTEGER NOT NULL);
        CREATE TABLE tournaments(
            id INTEGER PRIMARY KEY,start_date TEXT,end_date TEXT,sport TEXT,
            points_win INTEGER DEFAULT 3,points_draw INTEGER DEFAULT 1,points_loss INTEGER DEFAULT 0,
            table_tiebreak TEXT DEFAULT 'Målskillnad först',schedule_dirty INTEGER DEFAULT 0,is_published INTEGER DEFAULT 1
        );
        CREATE TABLE schedule_rules(
            tournament_id INTEGER PRIMARY KEY,halves INTEGER DEFAULT 2,minutes_per_half INTEGER DEFAULT 20,
            halftime_minutes INTEGER DEFAULT 5,pitch_break_minutes INTEGER DEFAULT 5,minimum_team_rest_minutes INTEGER DEFAULT 45,
            avoid_consecutive_matches INTEGER DEFAULT 1,consecutive_match_break_minutes INTEGER DEFAULT 15,
            pitch_count INTEGER DEFAULT 2,first_match_time TEXT DEFAULT '09:00',latest_kickoff_time TEXT DEFAULT '18:00'
        );
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE matches(
            id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,stage TEXT,match_no INTEGER,round_no INTEGER,
            home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,schedule_locked INTEGER DEFAULT 0,
            schedule_published INTEGER DEFAULT 1,home_score INTEGER,away_score INTEGER
        );
        INSERT INTO tournament_members VALUES(1,10);
        INSERT INTO tournaments(id,start_date,end_date,sport) VALUES(10,'2026-09-20','2026-09-20','Fotboll');
        INSERT INTO schedule_rules(tournament_id) VALUES(10);
        INSERT INTO groups VALUES(1,10,'Grupp A');
        INSERT INTO teams VALUES(1,10,'ÖSK');
        INSERT INTO teams VALUES(2,10,'Karlslund');
        INSERT INTO matches(id,tournament_id,group_id,stage,match_no,home_source,away_source) VALUES(1,10,1,'Gruppspel',1,'team:1','team:2');
        """
    )
    con.commit();con.close()


def _env(monkeypatch,path):
    monkeypatch.delenv('TURSO_DATABASE_URL',raising=False)
    monkeypatch.delenv('TURSO_AUTH_TOKEN',raising=False)
    monkeypatch.setenv('CUPNAVI_API_SQLITE_PATH',str(path))


def test_rules_update_marks_existing_schedule_dirty(monkeypatch,tmp_path):
    db=tmp_path/'v633.sqlite';_schema(db);_env(monkeypatch,db)
    con=sqlite3.connect(db);con.execute("UPDATE matches SET scheduled_start='2026-09-20T10:00',pitch_number=1 WHERE id=1");con.commit();con.close()
    saved=update_rules(1,10,{'minimum_team_rest_minutes':60,'points_win':4})
    assert saved['minimum_team_rest_minutes']==60
    assert saved['points_win']==4
    assert saved['schedule_dirty'] is True


def test_completed_match_blocks_structure_change(monkeypatch,tmp_path):
    db=tmp_path/'v633-completed.sqlite';_schema(db);_env(monkeypatch,db)
    con=sqlite3.connect(db);con.execute("UPDATE matches SET home_score=2,away_score=1 WHERE id=1");con.commit();con.close()
    with pytest.raises(ValueError,match='färdigspelade'):
        update_rules(1,10,{'minutes_per_half':25})
    assert admin_rules(1,10)['minutes_per_half']==20


def test_manual_schedule_update_unpublishes_without_moving_other_matches(monkeypatch,tmp_path):
    db=tmp_path/'v633-schedule.sqlite';_schema(db);_env(monkeypatch,db)
    saved=update_match_schedule(1,10,1,{'scheduled_start':'2026-09-20T11:15','pitch_number':2})
    row=saved['matches'][0]
    assert row['scheduled_start']=='2026-09-20T11:15'
    assert row['pitch_number']==2
    con=sqlite3.connect(db)
    tournament=con.execute('SELECT schedule_dirty,is_published FROM tournaments WHERE id=10').fetchone()
    published=con.execute('SELECT schedule_published FROM matches WHERE id=1').fetchone()[0]
    con.close()
    assert tournament==(1,0)
    assert published==0


def test_schedule_rejects_time_outside_cup(monkeypatch,tmp_path):
    db=tmp_path/'v633-window.sqlite';_schema(db);_env(monkeypatch,db)
    with pytest.raises(ValueError,match='efter cupens sista dag'):
        update_match_schedule(1,10,1,{'scheduled_start':'2026-09-21T10:00','pitch_number':1})


def test_v633_routes_exposed():
    routes={(route.path,method) for route in app.routes for method in getattr(route,'methods',set())}
    assert ('/api/admin/cups/{tournament_id}/rules','GET') in routes
    assert ('/api/admin/cups/{tournament_id}/rules','PUT') in routes
    assert ('/api/admin/cups/{tournament_id}/schedule','GET') in routes
    assert ('/api/admin/cups/{tournament_id}/schedule/matches/{match_id}','PUT') in routes
