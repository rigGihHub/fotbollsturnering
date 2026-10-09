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
from cupnavi_api.publish_reporting_repository import admin_reporting, reset_all_results, reset_result, save_result, set_reporter_match_status
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
        CREATE TABLE tournament_members(organizer_account_id INTEGER,tournament_id INTEGER,role TEXT DEFAULT 'admin');
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
        INSERT INTO tournament_members VALUES(7,1,'admin');
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


def test_public_snapshot_reuses_resolver_and_schema_reads_without_hidden_match_leak(cup, monkeypatch):
    from contextlib import contextmanager
    from cupnavi_api import participant_resolution_repository as resolution
    import_groups()
    with sqlite3.connect(cup) as con:
        for field in ('age_class','primary_color','secondary_color'):
            con.execute(f'ALTER TABLE teams ADD COLUMN {field} TEXT')
        con.execute("ALTER TABLE tournaments ADD COLUMN arena_address TEXT DEFAULT 'Örebro'")
        con.execute('CREATE TABLE venue_points(id INTEGER,tournament_id INTEGER,kind TEXT,label TEXT,detail TEXT,url TEXT)')
        con.execute("INSERT INTO matches(tournament_id,group_id,stage,home_source,away_source,schedule_published) VALUES(1,54,'Gruppspel','team:1','team:2',0)")
        con.execute('UPDATE tournaments SET is_published=1 WHERE id=1')
    connections,statements=[],[]
    @contextmanager
    def traced_connect():
        with sqlite3.connect(cup) as con:
            connections.append(con)
            con.row_factory=sqlite3.Row
            con.set_trace_callback(statements.append)
            yield con
    monkeypatch.setattr(db,'connect',traced_connect)
    result=resolution.resolve_public_snapshot(db.public_snapshot('1'))
    assert len(result['matches'])==18
    assert len(result['placement_groups'])==3
    assert all(m['schedule_published']==1 and m['scheduled_start'] for m in result['matches'])
    first_playoff=next(m for m in result['matches'] if m['bracket_id'])
    # The extra unpublished group game keeps group A unresolved even though it
    # is excluded from the public schedule; the faster path preserves parity.
    sidecar=result['participant_resolution'][str(first_playoff['id'])]
    assert not sidecar['home']['resolved'] or not sidecar['away']['resolved']
    assert len(connections)==2
    # SQLite's trace includes five internal PRAGMA comments; independent public
    # collections now share a single statement sent over the connection.
    assert len([sql for sql in statements if not sql.startswith('--')])==5
    connections.clear();statements.clear()
    fast=db.public_snapshot('1',resolve=True)
    assert {key:value for key,value in fast.items() if key!='standings'}=={key:value for key,value in result.items() if key!='standings'}
    assert len(connections)==1
    assert len([sql for sql in statements if not sql.startswith('--')])==4
    assert fast['standings']==standings('1')['groups']
    assert fast['standings'][0]['rows'][0]['S']==2
    assert all('tournament_id' not in row for row in fast['teams'])
    # Production uses the libsql row adapter and JSON functions, not sqlite.Row.
    import libsql
    @contextmanager
    def libsql_connect():
        con=libsql.connect(str(cup))
        try:
            yield con
        finally:
            con.close()
    monkeypatch.setattr(db,'connect',libsql_connect)
    assert db.public_snapshot('1',resolve=True)==fast


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


def test_local_admin_can_correct_finished_result_only_inside_assigned_cup(cup):
    match=db.one("SELECT * FROM matches WHERE tournament_id=1 AND match_status='finished' ORDER BY id LIMIT 1")

    corrected=save_result(7,1,match['id'],1,1,2,0)

    assert corrected['home_score']==1 and corrected['away_score']==1
    stored=db.one("SELECT home_score,away_score,match_status FROM matches WHERE id=?",(match['id'],))
    assert stored=={'home_score':1,'away_score':1,'match_status':'finished'}
    assert save_result(7,2,match['id'],3,0,1,1) is None


def test_local_admin_can_reset_saved_result_to_unplayed_and_clear_match_events(cup):
    match=db.one("SELECT * FROM matches WHERE tournament_id=1 AND match_status='finished' ORDER BY id LIMIT 1")
    with sqlite3.connect(cup) as con:
        con.execute('CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER,player_id INTEGER,goals INTEGER,assists INTEGER,yellow_cards INTEGER,red_cards INTEGER)')
        con.execute('CREATE TABLE match_goal_minutes(id INTEGER PRIMARY KEY,match_id INTEGER,side TEXT,minute INTEGER)')
        con.execute('INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards) VALUES(?,?,?,?,?,?)',(match['id'],1,2,0,0,0))
        con.execute('INSERT INTO match_goal_minutes(match_id,side,minute) VALUES(?,?,?)',(match['id'],'home',12))

    reset=reset_result(
        7,1,match['id'],match['home_score'],match['away_score'],
        expected_home_penalties=match['home_penalties'],
        expected_away_penalties=match['away_penalties'],
        expected_status='finished',
    )

    assert reset['home_score'] is None and reset['away_score'] is None
    assert reset['home_penalties'] is None and reset['away_penalties'] is None
    assert reset['match_status']=='not_started'
    assert reset['actual_elapsed_seconds']==0
    assert db.one('SELECT COUNT(*) AS n FROM player_match_stats WHERE match_id=?',(match['id'],))['n']==0
    assert db.one('SELECT COUNT(*) AS n FROM match_goal_minutes WHERE match_id=?',(match['id'],))['n']==0
    restored=next(item for item in admin_reporting(7,1)['matches'] if item['id']==match['id'])
    assert restored['status']=='scheduled'
    assert reset_result(7,2,match['id'],None,None,expected_status='not_started') is None


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


def test_goal_minutes_are_real_optional_and_removed_when_score_is_corrected(cup):
    from cupnavi_api.repository import public_snapshot
    with sqlite3.connect(cup) as con:
        con.execute('ALTER TABLE tournaments ADD COLUMN show_public_goal_minutes INTEGER DEFAULT 0')
        con.execute('ALTER TABLE teams ADD COLUMN age_class TEXT')
        con.execute('ALTER TABLE teams ADD COLUMN primary_color TEXT')
        con.execute('ALTER TABLE teams ADD COLUMN secondary_color TEXT')
        con.execute('CREATE TABLE venue_points(id INTEGER, tournament_id INTEGER, kind TEXT, label TEXT, detail TEXT, url TEXT)')
    match=db.one('SELECT id FROM matches WHERE tournament_id=1 ORDER BY id LIMIT 1')
    mid=match['id']
    save_result(7,1,mid,3,0,2,0,goal_minutes_home=[12])
    assert db.all_rows('SELECT side,minute FROM match_goal_minutes WHERE match_id=?',(mid,))==[{'side':'home','minute':12}]
    assert 'goal_minutes' not in public_snapshot('cup-1')['matches'][0]
    with sqlite3.connect(cup) as con:
        con.execute('UPDATE tournaments SET show_public_goal_minutes=1 WHERE id=1')
    assert public_snapshot('cup-1')['matches'][0]['goal_minutes']==[{'side':'home','minute':12}]
    save_result(7,1,mid,2,0,3,0)
    assert public_snapshot('cup-1')['matches'][0]['goal_minutes']==[]


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


def knockout_rows():
    return [
        {'label':'Semi 1','home_source':'A1','away_source':'B1','time':'14:00','venue':'Sörbyvallen'},
        {'label':'Semi 2','home_source':'C1','away_source':'A2','time':'15:00','venue':'Sörbyvallen'},
        {'label':'Final','home_source':'Vinnare Semi 1','away_source':'Vinnare Semi 2','time':'16:00','venue':'Sörbyvallen'},
    ]


def test_preview_replace_and_restore_playoff_format_keeps_group_results(cup):
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs, apply_group_playoffs, restore_previous_playoffs
    from cupnavi_core.placement_playoffs import GROUP_PLAYOFF_FORMAT
    commit_playoff_import(7,1,knockout_rows())
    before=db.all_rows('SELECT * FROM matches ORDER BY id')
    group_before=[row for row in before if row['bracket_id'] is None]
    preview=preview_group_playoffs(7,1,imported_rows(),'slottskampen.pdf')
    assert preview['replaced_count']==3 and preview['match_count']==9 and preview['scheduled_count']==9
    assert [g['name'] for g in preview['levels']]==['GULDGRUPPEN','SILVERGRUPPEN','BRONSGRUPPEN']
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    saved=apply_group_playoffs(7,1,preview['revision'],preview['matches'],preview['source_name'])
    assert saved['imported']==9
    state=admin_playoffs(7,1)
    assert state['playoff_format']==GROUP_PLAYOFF_FORMAT and state['placement_mode']
    assert state['restore_available']
    assert state['playoff_tie_rule']==DRAW_RULE and state['playoff_extra_time_minutes']==0
    assert db.all_rows('SELECT * FROM matches WHERE bracket_id IS NULL ORDER BY id')==group_before
    assert db.one('SELECT is_published,schedule_dirty FROM tournaments WHERE id=1')=={'is_published':0,'schedule_dirty':1}
    assert restore_previous_playoffs(7,1)['restored']
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    assert not admin_playoffs(7,1)['restore_available']


def test_group_plan_stale_preview_started_match_and_wrong_pdf_are_blocked(cup):
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs, apply_group_playoffs
    commit_playoff_import(7,1,knockout_rows())
    preview=preview_group_playoffs(7,1,imported_rows())
    with sqlite3.connect(cup) as con:
        con.execute("UPDATE matches SET scheduled_start='2026-10-24T13:00' WHERE bracket_id IS NOT NULL AND stage='Semi 1'")
    with pytest.raises(ValueError,match='ändrats sedan'):
        apply_group_playoffs(7,1,preview['revision'],preview['matches'])
    assert admin_playoffs(7,1)['match_count']==3
    with pytest.raises(ValueError,match='underlaget|Underlaget'):
        preview_group_playoffs(7,1,[{**imported_rows()[0],'home_source':'1:a grupp D'}])
    with sqlite3.connect(cup) as con:
        con.execute("UPDATE matches SET match_status='live' WHERE bracket_id IS NOT NULL AND stage='Semi 1'")
    with pytest.raises(ValueError,match='startats'):
        preview_group_playoffs(7,1,imported_rows())
    assert preview_group_playoffs(7,2,[]) is None


def test_group_plan_uses_existing_rank_pairs_without_moving_times(cup):
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs
    import_groups()
    before=db.all_rows('SELECT * FROM matches WHERE bracket_id IS NOT NULL ORDER BY id')
    preview=preview_group_playoffs(7,1)
    expected={tuple(sorted((row['home_source'],row['away_source']))):row['scheduled_start'] for row in before}
    assert preview['source_name']=='Befintligt placeringsgruppspel'
    for row in preview['matches']:
        from cupnavi_api.playoff_import_repository import _resolve_source
        group_map={'a':54,'b':55,'c':56}
        home,_=_resolve_source(row['home_source'],{},group_map,{})
        away,_=_resolve_source(row['away_source'],{},group_map,{})
        assert row['time']==expected[tuple(sorted((home,away)))]


def test_group_plan_api_returns_real_new_format_and_scope(cup):
    app=FastAPI();register_competition_admin_routes(app,lambda _: {'id':7});client=TestClient(app)
    preview=client.post('/api/admin/cups/1/playoffs/group-plan/preview',json={'source_rows':[]})
    assert preview.status_code==200
    assert preview.json()['scheduled_count']==0
    result=client.post('/api/admin/cups/1/playoffs/group-plan/apply',json={'revision':preview.json()['revision'],'source_rows':preview.json()['matches']})
    assert result.status_code==200,result.text
    assert result.json()['placement_mode'] and result.json()['match_count']==9
    assert client.post('/api/admin/cups/2/playoffs/group-plan/preview',json={}).status_code==404
    assert client.post('/api/admin/cups/1/playoffs/group-plan/restore').status_code==200

@pytest.mark.parametrize('table', ['match_events', 'player_match_stats', 'match_goal_minutes'])
def test_group_plan_events_without_score_block_preview_and_restore(cup, table):
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs, apply_group_playoffs, restore_previous_playoffs
    commit_playoff_import(7,1,knockout_rows())
    proposal=preview_group_playoffs(7,1,imported_rows())
    apply_group_playoffs(7,1,proposal['revision'],proposal['matches'])
    match_id=db.one('SELECT id FROM matches WHERE bracket_id IS NOT NULL')['id']
    with sqlite3.connect(cup) as con:
        con.execute(f'CREATE TABLE IF NOT EXISTS {table}(match_id INTEGER)')
        columns={row[1] for row in con.execute(f'PRAGMA table_info({table})')}
        if table=='match_goal_minutes' and 'side' in columns:
            con.execute(f"INSERT INTO {table}(match_id,side,minute) VALUES(?,'home',1)", (match_id,))
        else:
            con.execute(f'INSERT INTO {table}(match_id) VALUES(?)', (match_id,))
    before=db.all_rows('SELECT * FROM matches ORDER BY id')
    with pytest.raises(ValueError,match='matchhändelser'):
        preview_group_playoffs(7,1,[])
    with pytest.raises(ValueError,match='matchhändelser'):
        restore_previous_playoffs(7,1)
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    assert not admin_playoffs(7,1)['restore_available']


def test_group_plan_rejects_ambiguous_pitch_names(cup):
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs
    with sqlite3.connect(cup) as con:
        con.executemany('INSERT INTO pitches VALUES(1,?,?)', [(1,'Sörbyvallen'),(2,'Sörbyvallen')])
    with pytest.raises(ValueError,match='unika namn'):
        preview_group_playoffs(7,1,imported_rows())


def test_reviewed_initial_playoffs_retry_does_not_duplicate_or_overwrite(cup):
    app=FastAPI();register_competition_admin_routes(app,lambda _: {'id':7});client=TestClient(app)
    payload={'playoff_matches':imported_rows(),'playoff_rule_values':{'tie_rule':DRAW_RULE},'reviewed_retry':True}
    first=client.post('/api/admin/cups/1/import/playoffs',json=payload)
    assert first.status_code==200,first.text
    before=db.all_rows('SELECT * FROM matches ORDER BY id')
    replay=client.post('/api/admin/cups/1/import/playoffs',json=payload)
    assert replay.status_code==200 and replay.json()['idempotent_replay']
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    assert admin_playoffs(7,1)['placement_mode']
    assert client.post('/api/admin/cups/2/import/playoffs',json=payload).status_code==404
    changed={**payload,'playoff_matches':[{**row,'time':'19:00'} for row in imported_rows()]}
    assert client.post('/api/admin/cups/1/import/playoffs',json=changed).status_code==422
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==before
    with sqlite3.connect(cup) as con:
        con.execute("UPDATE matches SET scheduled_start='2026-10-24T19:00' WHERE bracket_id IS NOT NULL")
    edited=db.all_rows('SELECT * FROM matches ORDER BY id')
    assert client.post('/api/admin/cups/1/import/playoffs',json=payload).status_code==422
    assert db.all_rows('SELECT * FROM matches ORDER BY id')==edited


def test_preview_keeps_unscheduled_playoff_groups_without_public_leak(cup, monkeypatch):
    import cupnavi_api.main as main
    from cupnavi_api.repository import public_snapshot
    from cupnavi_api.playoff_group_plan_repository import preview_group_playoffs, apply_group_playoffs
    with sqlite3.connect(cup) as con:
        for field in ('age_class','primary_color','secondary_color'):
            con.execute(f'ALTER TABLE teams ADD COLUMN {field} TEXT')
        con.execute('CREATE TABLE venue_points(id INTEGER,tournament_id INTEGER,kind TEXT,label TEXT,detail TEXT,url TEXT)')
    preview=preview_group_playoffs(7,1,[])
    apply_group_playoffs(7,1,preview['revision'],preview['matches'])
    monkeypatch.setattr(main,'_admin_identity',lambda _: {'id':7})
    monkeypatch.setattr(main,'admin_cupinfo',lambda account,tid: {'id':tid} if tid==1 else None)
    result=main.admin_cup_preview(1,None)
    assert len(result['cup']['matches'])==18
    assert len(result['cup']['placement_groups'])==3
    assert sum(len(b['matches']) for b in result['cup']['brackets'])==9
    assert result['pending_playoff_count']==0
    assert public_snapshot('cup-1') is None
    with sqlite3.connect(cup) as con:
        con.execute('UPDATE tournaments SET is_published=1 WHERE id=1')
        con.execute('UPDATE matches SET schedule_published=1 WHERE tournament_id=1')
    public=resolve_public_snapshot(public_snapshot('cup-1'))
    assert len(public['matches'])==9
    assert all(not bracket['matches'] for bracket in public['brackets'])
    assert public['placement_groups']==[]


def test_preview_explains_staged_playoffs_instead_of_silently_hiding_them(cup, monkeypatch):
    import json
    import cupnavi_api.main as main
    from cupnavi_core.migrations import ensure_v35_schema_compat
    with sqlite3.connect(cup) as con:
        for field in ('age_class','primary_color','secondary_color'):
            con.execute(f'ALTER TABLE teams ADD COLUMN {field} TEXT')
        con.execute('CREATE TABLE venue_points(id INTEGER,tournament_id INTEGER,kind TEXT,label TEXT,detail TEXT,url TEXT)')
        ensure_v35_schema_compat(con)
        con.execute("INSERT INTO tournament_setup_imports(tournament_id,import_kind,payload_json) VALUES(1,'initial_setup',?)",(json.dumps({'playoff_matches':imported_rows()}),))
    monkeypatch.setattr(main,'_admin_identity',lambda _: {'id':7})
    monkeypatch.setattr(main,'admin_cupinfo',lambda account,tid: {'id':tid} if tid==1 else None)
    assert main.admin_cup_preview(1,None)['pending_playoff_count']==9
    import_groups()
    assert main.admin_cup_preview(1,None)['pending_playoff_count']==0


def test_reset_all_clears_group_and_playoff_results_and_events_but_preserves_other_cup(cup):
    import_groups()
    admin_reporting(7, 1)  # Existing databases acquire clock columns first.
    with sqlite3.connect(cup) as con:
        con.executescript('''
        CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER,goals INTEGER,assists INTEGER,yellow_cards INTEGER,red_cards INTEGER);
        CREATE TABLE match_goal_minutes(id INTEGER PRIMARY KEY,match_id INTEGER,side TEXT,minute INTEGER);
        INSERT INTO matches(id,tournament_id,stage,home_score,away_score,match_status) VALUES(987,2,'Final',9,8,'finished');
        INSERT INTO player_match_stats VALUES(1,1,2,1,1,1),(2,987,9,0,0,0);
        INSERT INTO match_goal_minutes VALUES(1,1,'home',12),(2,987,'home',8);
        UPDATE matches SET home_score=2,away_score=2,home_penalties=4,away_penalties=3,decided_winner_id=1,
            match_status=CASE WHEN bracket_id IS NULL THEN 'finished' ELSE 'live' END,
            actual_started_at='2026-10-09T12:00:00',actual_finished_at='2026-10-09T12:10:00',
            actual_paused_at='2026-10-09T12:05:00',actual_elapsed_seconds=300 WHERE tournament_id=1;
        ''')
    structure_sql = 'SELECT id,tournament_id,group_id,bracket_id,stage,home_source,away_source,scheduled_start,pitch_number,schedule_published,schedule_locked FROM matches ORDER BY id'
    before = db.all_rows(structure_sql)
    tournament = db.one('SELECT * FROM tournaments WHERE id=1')
    assert reset_all_results(7, 1, 18) == {'reset_count': 18}
    matches = db.all_rows('SELECT * FROM matches WHERE tournament_id=1')
    assert len(matches) == 18
    for match in matches:
        for field in ('home_score','away_score','home_penalties','away_penalties','decided_winner_id','actual_started_at','actual_finished_at','actual_paused_at'):
            assert match[field] is None
        assert match['match_status'] == 'not_started'
        assert match['actual_elapsed_seconds'] == 0
    assert db.all_rows(structure_sql) == before
    assert db.one('SELECT * FROM tournaments WHERE id=1') == tournament
    assert db.one('SELECT home_score,away_score,match_status FROM matches WHERE id=987') == {'home_score':9,'away_score':8,'match_status':'finished'}
    assert [row['match_id'] for row in db.all_rows('SELECT * FROM player_match_stats')] == [987]
    assert [row['match_id'] for row in db.all_rows('SELECT * FROM match_goal_minutes')] == [987]
    assert all(match['status'] == 'scheduled' for match in admin_reporting(7,1)['matches'])
    assert reset_all_results(7, 1, 18) == {'reset_count': 18}


def test_reset_all_rejects_wrong_scope_or_changed_match_count(cup):
    before = db.all_rows('SELECT * FROM matches ORDER BY id')
    assert reset_all_results(7, 2, 0) is None
    with pytest.raises(RuntimeError, match='Antalet matcher har ändrats'):
        reset_all_results(7, 1, 8)
    assert [(m['home_score'],m['away_score'],m['match_status']) for m in db.all_rows('SELECT * FROM matches ORDER BY id')] == [(m['home_score'],m['away_score'],m['match_status']) for m in before]


def test_reset_all_rolls_back_entire_cup_if_event_cleanup_fails(cup):
    admin_reporting(7, 1)
    with sqlite3.connect(cup) as con:
        con.executescript('''
        CREATE TABLE player_match_stats(id INTEGER PRIMARY KEY,match_id INTEGER,goals INTEGER);
        INSERT INTO player_match_stats VALUES(1,1,2);
        CREATE TRIGGER reject_event_cleanup BEFORE DELETE ON player_match_stats BEGIN SELECT RAISE(ABORT,'test cleanup failure'); END;
        ''')
    before = db.all_rows('SELECT * FROM matches ORDER BY id')
    with pytest.raises(sqlite3.IntegrityError, match='test cleanup failure'):
        reset_all_results(7, 1, 9)
    assert db.all_rows('SELECT * FROM matches ORDER BY id') == before
    assert db.one('SELECT COUNT(*) AS n FROM player_match_stats')['n'] == 1


def test_reset_all_route_requires_admin_confirmation_and_cup_access(cup):
    from fastapi import HTTPException
    from cupnavi_api.publish_reporting_routes import register_publish_reporting_routes
    def identity(authorization):
        if authorization != 'Bearer local-admin':
            raise HTTPException(401, 'Admin session required')
        return {'id':7}
    app=FastAPI()
    register_publish_reporting_routes(app,identity)
    client=TestClient(app)
    url='/api/admin/cups/1/reporting/reset-all'
    payload={'confirmed':True,'expected_match_count':9}
    headers={'Authorization':'Bearer local-admin'}
    assert client.post(url,json=payload).status_code == 401
    assert client.post(url,headers={'Authorization':'Bearer reporter'},json=payload).status_code == 401
    assert client.post(url,headers=headers,json={**payload,'confirmed':False}).status_code == 422
    assert client.post(url,headers=headers,json={'expected_match_count':9}).status_code == 422
    assert client.post('/api/admin/cups/2/reporting/reset-all',headers=headers,json=payload).status_code == 404
    assert client.post(url,headers=headers,json={**payload,'expected_match_count':8}).status_code == 409
    assert db.one('SELECT COUNT(*) AS n FROM matches WHERE home_score IS NOT NULL')['n'] == 9
    response=client.post(url,headers=headers,json=payload)
    assert response.status_code == 200 and response.json() == {'reset_count':9}
    assert db.one('SELECT COUNT(*) AS n FROM matches WHERE home_score IS NOT NULL')['n'] == 0
