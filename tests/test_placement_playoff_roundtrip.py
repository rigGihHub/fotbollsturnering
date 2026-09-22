"""Cup-day regression: imported placement groups are tables, not knockout trees."""
import sqlite3
from itertools import combinations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cupnavi_api import repository as db
from cupnavi_api.competition_admin_routes import register_competition_admin_routes
from cupnavi_api.playoff_import_repository import commit_playoff_import
from cupnavi_api.playoff_admin_repository import admin_playoffs, update_playoff_settings
from cupnavi_api.publish_reporting_repository import admin_reporting, save_result, set_reporter_match_status
from cupnavi_api.participant_resolution_repository import resolve_public_snapshot
from cupnavi_api.main import playoffs, standings
from cupnavi_core.placement_playoffs import DRAW_RULE, all_placement_blocks


@pytest.fixture
def cup(tmp_path, monkeypatch):
    path = tmp_path / 'cup.db'
    monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    monkeypatch.delenv('TURSO_AUTH_TOKEN', raising=False)
    monkeypatch.setenv('CUPNAVI_API_SQLITE_PATH', str(path))
    with sqlite3.connect(path) as con:
        con.executescript('''
        CREATE TABLE tournament_members(organizer_account_id INTEGER,tournament_id INTEGER);
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT,public_slug TEXT,start_date TEXT,
            playoff_format TEXT DEFAULT 'Manuellt slutspel',bronze_match INTEGER DEFAULT 0,
            playoff_tie_rule TEXT DEFAULT 'Straffar direkt',extra_time_minutes INTEGER DEFAULT 10,
            schedule_dirty INTEGER DEFAULT 0,is_published INTEGER DEFAULT 1,admin_revision INTEGER DEFAULT 0,
            arrangement_type TEXT DEFAULT 'tournament_playoffs',points_win INTEGER DEFAULT 3,
            points_draw INTEGER DEFAULT 1,points_loss INTEGER DEFAULT 0,table_tiebreak TEXT DEFAULT 'Målskillnad först');
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,group_id INTEGER);
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,age_class TEXT);
        CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT);
        CREATE TABLE brackets(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT,size INTEGER,bronze_match INTEGER);
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,group_id INTEGER,bracket_id INTEGER,
            stage TEXT,round_no INTEGER,match_no INTEGER,home_source TEXT,away_source TEXT,scheduled_start TEXT,
            pitch_number INTEGER,home_score INTEGER,away_score INTEGER,home_penalties INTEGER,away_penalties INTEGER,
            decided_winner_id INTEGER,schedule_locked INTEGER DEFAULT 0,schedule_published INTEGER DEFAULT 1,
            match_status TEXT DEFAULT 'not_started',status_updated_at TEXT,actual_started_at TEXT,actual_finished_at TEXT);
        INSERT INTO tournament_members VALUES(7,1);
        INSERT INTO tournaments(id,name,public_slug,start_date) VALUES(1,'Cup 1','cup-1','2026-10-24'),(2,'Annan cup','cup-2','2026-10-24');
        ''')
        for index, name in enumerate(('A','B','C')):
            gid=54+index
            con.execute('INSERT INTO groups VALUES(?,1,?,NULL)', (gid,name))
            ids=[index*3+rank for rank in (1,2,3)]
            con.executemany('INSERT INTO teams VALUES(?,1,?,?)', [(tid,f'{name}{rank}',gid) for rank,tid in enumerate(ids,1)])
            for home, away in combinations(ids,2):
                con.execute("INSERT INTO matches(tournament_id,group_id,stage,home_source,away_source,home_score,away_score,match_status,scheduled_start) VALUES(1,?,'Gruppspel',?,?,2,0,'finished','2026-10-24T09:00')", (gid,f'team:{home}',f'team:{away}'))
    return path


def imported_rows():
    return [{'label':name,'home_source':f'{rank}:a grupp {h}','away_source':f'{rank}:a grupp {a}',
             'time':f'{14+rank}:00','venue':'Sörbyvallen'}
            for rank,name in ((1,'GULDGRUPPEN'),(2,'SILVERGRUPPEN'),(3,'BRONSGRUPPEN'))
            for h,a in combinations(('A','B','C'),2)]


def import_groups(draw=True):
    return commit_playoff_import(7,1,imported_rows(),{'tie_rule':'Alla matcher får sluta oavgjort. Ingen förlängning eller straffar.'} if draw else {})


def test_import_saves_explicit_draw_rule_and_real_participant_count(cup):
    result=import_groups()
    assert result['imported']==9
    state=admin_playoffs(7,1)
    assert state['playoff_tie_rule']==DRAW_RULE
    assert state['playoff_extra_time_minutes']==0  # actual DB column is extra_time_minutes
    assert state['placement_mode'] is True
    assert state['bronze_match'] is False
    assert state['brackets'][0]['size']==9
    assert state['brackets'][0]['bronze_match']==0
    assert [g['name'] for g in state['placement_groups']]==['GULDGRUPPEN','SILVERGRUPPEN','BRONSGRUPPEN']
    assert state['brackets'][0]['matches'][0]['home_source_label']=='1:a i grupp A'
    assert state['brackets'][0]['matches'][0]['away_source_label']=='1:a i grupp B'
    assert all(g['winner'] is None for g in state['placement_groups'])


def test_existing_import_can_be_switched_via_api_without_reimport(cup):
    import_groups(draw=False)
    before=db.all_rows('SELECT * FROM matches ORDER BY id')
    with sqlite3.connect(cup) as con:
        con.execute("CREATE TRIGGER dirty AFTER UPDATE OF playoff_tie_rule,extra_time_minutes ON tournaments BEGIN UPDATE tournaments SET schedule_dirty=1 WHERE id=NEW.id; END")
    app=FastAPI()
    register_competition_admin_routes(app,lambda _: {'id':7})
    api=TestClient(app)
    response=api.put('/api/admin/cups/1/playoffs',json={'playoff_tie_rule':DRAW_RULE})
    assert response.status_code==200, response.text
    assert response.json()['placement_mode'] is True
    assert db.one('SELECT schedule_dirty FROM tournaments WHERE id=1')['schedule_dirty']==0
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    assert db.one('SELECT extra_time_minutes FROM tournaments WHERE id=1')['extra_time_minutes']==0
    assert api.put('/api/admin/cups/2/playoffs',json={'playoff_tie_rule':DRAW_RULE}).status_code==404
    assert db.one('SELECT playoff_tie_rule FROM tournaments WHERE id=2')['playoff_tie_rule']=='Straffar direkt'


def test_draw_result_finishes_without_penalties_and_public_endpoints_agree(cup):
    import_groups()
    matches=[m for m in admin_reporting(7,1)['matches'] if m['bracket_id']]
    match=matches[0]
    assert match['requires_winner'] is False
    set_reporter_match_status(7,1,match['id'],'live','not_started')
    saved=save_result(7,1,match['id'],1,1,None,None)
    assert saved['status']=='played' and saved['outcome_resolved']
    assert saved['home_penalties'] is None and saved['decided_winner_id'] is None
    # A live score must not prematurely count as a completed placement game.
    assert admin_playoffs(7,1)['placement_groups'][0]['rows'][0]['S']==0
    set_reporter_match_status(7,1,match['id'],'finished','live')
    with sqlite3.connect(cup) as con:
        con.execute('UPDATE tournaments SET is_published=1 WHERE id=1')
    raw={'tournament':db.public_tournament('cup-1'),'matches':db.public_matches(1)}
    snapshot=resolve_public_snapshot(raw)
    a=snapshot['placement_groups']
    assert a==playoffs('cup-1')['placement_groups']==standings('cup-1')['placement_groups']
    assert sorted(r['P'] for r in a[0]['rows'])==[0,1,1]
    assert a[0]['winner'] is None
    with pytest.raises(RuntimeError,match='ändrats'):
        save_result(7,1,match['id'],4,0,None,None)
    with pytest.raises(ValueError,match='spelats'):
        update_playoff_settings(7,1,{'playoff_tie_rule':'Straffar direkt'})
    with pytest.raises(ValueError,match='inga straffar'):
        save_result(7,1,match['id'],1,1,1,1,home_penalties=4,away_penalties=3)


def test_group_winner_and_corrected_draw_recalculate_without_alphabetical_champion(cup):
    import_groups()
    games=admin_playoffs(7,1)['brackets'][0]['matches'][:3]
    for game in games:
        save_result(7,1,game['id'],0,0,None,None)
    gold=admin_playoffs(7,1)['placement_groups'][0]
    assert gold['complete'] and gold['ranking_tied'] and gold['winner'] is None
    save_result(7,1,games[0]['id'],2,0,0,0)
    gold=admin_playoffs(7,1)['placement_groups'][0]
    assert gold['winner']=='A1' and not gold['ranking_tied']
    assert [(r['Lag'],r['P']) for r in gold['rows']]==[('A1',4),('C1',2),('B1',1)]
    save_result(7,1,games[0]['id'],0,0,2,0)
    assert admin_playoffs(7,1)['placement_groups'][0]['winner'] is None


def test_knockout_cannot_choose_draw_rule_or_finish_tied(cup):
    commit_playoff_import(7,1,[{'label':'Final','home_source':'A1','away_source':'B1','time':'16:00'}])
    with pytest.raises(ValueError,match='kompletta placeringsgrupper'):
        update_playoff_settings(7,1,{'playoff_tie_rule':DRAW_RULE})
    game=admin_playoffs(7,1)['brackets'][0]['matches'][0]
    set_reporter_match_status(7,1,game['id'],'live','not_started')
    assert save_result(7,1,game['id'],1,1,None,None)['status']=='awaiting_decision'
    with pytest.raises(ValueError,match='utslagsmatch'):
        set_reporter_match_status(7,1,game['id'],'finished','live')
    save_result(7,1,game['id'],1,1,1,1,home_penalties=4,away_penalties=3)
    assert set_reporter_match_status(7,1,game['id'],'finished','live')['match_status']=='finished'


def test_missing_duplicate_or_winner_dependent_group_is_not_accepted(cup):
    import_groups()
    matches=db.all_rows('SELECT * FROM matches')
    assert all_placement_blocks(matches)
    assert not all_placement_blocks(matches[:-1])
    assert not all_placement_blocks(matches+[matches[-1]])
    assert not all_placement_blocks(matches+[{'id':999,'home_source':f"winner:{matches[-1]['id']}"}])


def test_competing_rule_change_does_not_accept_stale_penalty_save(cup, monkeypatch):
    import_groups(draw=False)
    import cupnavi_api.publish_reporting_repository as reporting
    game=admin_playoffs(7,1)['brackets'][0]['matches'][0]
    original=reporting.prepare_result
    def changed_rules(**kwargs):
        prepared=original(**kwargs)
        update_playoff_settings(7,1,{'playoff_tie_rule':DRAW_RULE})
        return prepared
    monkeypatch.setattr(reporting,'prepare_result',changed_rules)
    with pytest.raises(RuntimeError,match='ändrats'):
        save_result(7,1,game['id'],1,1,None,None,home_penalties=4,away_penalties=3)
    row=db.one('SELECT * FROM matches WHERE id=?',(game['id'],))
    assert row['home_score'] is None and row['home_penalties'] is None


def test_starting_match_locks_the_tie_rule_even_before_any_goal(cup):
    import_groups(draw=False)
    game=admin_playoffs(7,1)['brackets'][0]['matches'][0]
    set_reporter_match_status(7,1,game['id'],'live','not_started')
    assert admin_playoffs(7,1)['rules_locked']
    with pytest.raises(ValueError,match='startats'):
        update_playoff_settings(7,1,{'playoff_tie_rule':DRAW_RULE})
