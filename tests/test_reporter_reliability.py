from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import cupnavi_api.publish_reporting_repository as reporting
import cupnavi_api.role_access_routes as roles
from cupnavi_api.repository import connect, one


@pytest.fixture
def match_client(tmp_path, monkeypatch):
    monkeypatch.delenv('TURSO_DATABASE_URL', raising=False)
    monkeypatch.delenv('TURSO_AUTH_TOKEN', raising=False)
    monkeypatch.setenv('CUPNAVI_API_SQLITE_PATH', str(tmp_path / 'matches.db'))
    monkeypatch.setattr(roles, '_reporter_identity', lambda _: {'tid': 1})
    monkeypatch.setattr(reporting, '_has_tournament_access', lambda *_: True)
    monkeypatch.setattr(reporting, '_resolver_for_tournament', lambda _: None)
    with connect() as con:
        con.executescript('''
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT,public_slug TEXT,arrangement_type TEXT);
        INSERT INTO tournaments VALUES(1,'Matchcup','matchcup','matchcamp');
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,stage TEXT,home_source TEXT,away_source TEXT,
          home_score INTEGER,away_score INTEGER,home_penalties INTEGER,away_penalties INTEGER,decided_winner_id INTEGER,
          match_status TEXT,status_updated_at TEXT,actual_started_at TEXT,actual_finished_at TEXT,
          actual_elapsed_seconds INTEGER DEFAULT 0,actual_paused_at TEXT,scheduled_start TEXT);
        INSERT INTO matches(id,tournament_id,stage,home_score,away_score,match_status,actual_elapsed_seconds,actual_finished_at)
          VALUES(10,1,'Gruppspel',0,0,'finished',16,'2026-10-09T10:00:16'),(20,2,'Gruppspel',0,0,'finished',16,NULL);
        ''')
        con.commit()
    app = FastAPI()
    roles.register_role_access_routes(app, lambda _: {'id': 1})
    return TestClient(app)


def test_finished_match_can_be_corrected_and_finished_again(match_client):
    url = '/api/reporter/reporting/matches/10'
    assert match_client.put(url, json={'home_score': 1, 'away_score': 0, 'expected_home_score': 0, 'expected_away_score': 0}).status_code == 409
    response = match_client.put(url + '/status', json={'status': 'halftime', 'expected_status': 'finished'})
    assert response.status_code == 200
    assert response.json()['actual_elapsed_seconds'] == 16
    assert response.json()['actual_started_at'] is None
    assert response.json()['actual_finished_at'] is None
    assert match_client.put(url, json={'home_score': 1, 'away_score': 0, 'expected_home_score': 0, 'expected_away_score': 0}).status_code == 200
    assert match_client.put(url + '/status', json={'status': 'finished', 'expected_status': 'halftime'}).status_code == 200
    saved = one('SELECT * FROM matches WHERE id=10')
    assert (saved['home_score'], saved['away_score'], saved['actual_elapsed_seconds']) == (1, 0, 16)


def test_resume_preserves_clock_and_rejects_stale_or_other_cup(match_client):
    url = '/api/reporter/reporting/matches/'
    response = match_client.put(url + '10/status', json={'status': 'live', 'expected_status': 'finished'})
    assert response.status_code == 200
    assert response.json()['actual_elapsed_seconds'] == 16
    assert response.json()['actual_started_at']
    assert match_client.put(url + '10/status', json={'status': 'halftime', 'expected_status': 'finished'}).status_code == 409
    assert match_client.put(url + '20/status', json={'status': 'live', 'expected_status': 'finished'}).status_code == 404
    assert one('SELECT match_status FROM matches WHERE id=20')['match_status'] == 'finished'


def test_reporter_score_cannot_race_a_finished_status(match_client, monkeypatch):
    with connect() as con:
        con.execute("UPDATE matches SET match_status='live' WHERE id=10")
        con.commit()
    original_connect = reporting.connect

    @contextmanager
    def finish_just_before_score_write():
        with original_connect() as con:
            class FinishBeforeWrite:
                def execute(self, sql, params=()):
                    if sql.lstrip().startswith('UPDATE matches'):
                        con.execute("UPDATE matches SET match_status='finished' WHERE id=10")
                        con.commit()
                    return con.execute(sql, params)
                def commit(self):
                    con.commit()
            yield FinishBeforeWrite()

    monkeypatch.setattr(reporting, 'connect', finish_just_before_score_write)
    response = match_client.put('/api/reporter/reporting/matches/10', json={'home_score': 1, 'away_score': 0, 'expected_home_score': 0, 'expected_away_score': 0})
    assert response.status_code == 409
    assert one('SELECT home_score FROM matches WHERE id=10')['home_score'] == 0


def test_live_elapsed_value_contains_one_live_segment():
    started = datetime.now(timezone.utc) - timedelta(seconds=30)
    elapsed = reporting._clock_elapsed_seconds({'match_status': 'live', 'actual_elapsed_seconds': 16, 'actual_started_at': started.isoformat()})
    assert 45 <= elapsed <= 47


@pytest.mark.parametrize('existing', [False, True])
def test_reporter_event_write_cannot_race_a_finished_status(match_client, monkeypatch, existing):
    import cupnavi_api.match_events_admin_repository as events
    monkeypatch.setattr(events, '_has_tournament_access', lambda *_: True)
    detail = {'teams': [{'team_score': 0, 'players': [{'id': 5, 'goals': 0, 'assists': 0, 'yellow_cards': 0, 'red_cards': 0}]}]}
    monkeypatch.setattr(events, 'admin_match_events', lambda *_: detail)
    with connect() as con:
        con.execute("UPDATE matches SET match_status='live' WHERE id=10")
        con.execute('CREATE TABLE player_match_stats(match_id INTEGER,player_id INTEGER,goals INTEGER,assists INTEGER,yellow_cards INTEGER,red_cards INTEGER,PRIMARY KEY(match_id,player_id))')
        if existing:
            con.execute('INSERT INTO player_match_stats VALUES(10,5,0,0,0,0)')
        con.commit()
    original_connect = events.connect

    @contextmanager
    def finish_before_event_write():
        with original_connect() as con:
            class FinishBeforeWrite:
                def execute(self, sql, params=()):
                    con.execute("UPDATE matches SET match_status='finished' WHERE id=10")
                    con.commit()
                    return con.execute(sql, params)
                def commit(self):
                    con.commit()
            yield FinishBeforeWrite()

    monkeypatch.setattr(events, 'connect', finish_before_event_write)
    with pytest.raises(RuntimeError):
        events.update_player_match_events(1, 1, 10, 5, {'goals': 0, 'assists': 0, 'yellow_cards': 1, 'red_cards': 0,
          'expected': {'goals': 0, 'assists': 0, 'yellow_cards': 0, 'red_cards': 0}}, reporter_edit=True)
    saved = one('SELECT * FROM player_match_stats WHERE match_id=10 AND player_id=5')
    assert saved is None or saved['yellow_cards'] == 0


def test_offline_pause_resume_and_finish_keep_time_from_button_press(match_client):
    url = '/api/reporter/reporting/matches/10/status'
    assert match_client.put(url, json={'status': 'live', 'expected_status': 'finished', 'elapsed_seconds': 16}).status_code == 200
    paused = match_client.put(url, json={'status': 'halftime', 'expected_status': 'live', 'elapsed_seconds': 76})
    assert paused.status_code == 200
    assert paused.json()['actual_elapsed_seconds'] == 76
    assert match_client.put(url, json={'status': 'live', 'expected_status': 'halftime', 'elapsed_seconds': 76}).status_code == 200
    finished = match_client.put(url, json={'status': 'finished', 'expected_status': 'live', 'elapsed_seconds': 136})
    assert finished.status_code == 200
    assert finished.json()['actual_elapsed_seconds'] == 136
    assert match_client.put(url, json={'status': 'live', 'expected_status': 'finished', 'elapsed_seconds': -1}).status_code == 422
