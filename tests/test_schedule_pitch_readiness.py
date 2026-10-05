import json
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cupnavi_core.schedule_pitch_readiness import pitch_window_readiness
from cupnavi_api import schedule_admin_repository as schedule
from cupnavi_api import venue_admin_repository as venues
from cupnavi_api import publish_reporting_repository as publication


RULES = {"halves": 2, "minutes_per_half": 18, "halftime_minutes": 2}


def match(number, time, pitch=1):
    return {"id": number, "match_no": number, "scheduled_start": f"2026-10-24T{time}", "pitch_number": pitch}


def window(start="08:30", end="19:18", pitch=1, confirmed=True, **extra):
    return {"pitch_number": pitch, "play_date": "2026-10-24", "start_time": start, "end_time": end, "confirmed": confirmed, **extra}


def test_slottskampen_18_matches_expose_required_times_including_match_end():
    times = [("08:30",1),("09:15",1),("10:00",2),("10:00",1),("10:45",1),("11:30",1),("12:15",1),("13:00",1),("13:45",1),("14:30",1),("15:15",2),("15:20",1),("16:10",1),("16:55",2),("17:00",1),("17:50",1),("18:35",2),("18:40",1)]
    matches = [match(i, time, pitch) for i, (time, pitch) in enumerate(times,1)]
    result = pitch_window_readiness(matches, RULES, [window(confirmed=False)])
    assert not result["ready"]
    assert len(result["issues"]) == 2
    assert result["requirements"] == [
        {"pitch_number":1,"play_date":"2026-10-24","first_start":"2026-10-24T08:30:00","last_end":"2026-10-24T19:18:00","match_count":14},
        {"pitch_number":2,"play_date":"2026-10-24","first_start":"2026-10-24T10:00:00","last_end":"2026-10-24T19:13:00","match_count":4},
    ]
    assert pitch_window_readiness(matches, RULES, [window(),window("10:00","19:13",pitch=2)])["ready"]


def test_closed_gap_and_match_end_cannot_be_approved():
    passes = [window("08:00","10:00",additional_windows_json=json.dumps([{"start_time":"11:00","end_time":"19:18"}]))]
    assert pitch_window_readiness([match(1,"09:30")],RULES,passes)["issues"][0]["type"] == "outside_window"
    assert pitch_window_readiness([match(1,"10:15")],RULES,passes)["issues"][0]["type"] == "outside_window"
    assert pitch_window_readiness([match(1,"18:40")],RULES,passes)["ready"]
    assert not pitch_window_readiness([match(1,"18:41")],RULES,passes)["ready"]


def test_wrong_day_missing_pitch_and_unconfirmed_windows_are_blocked():
    assert not pitch_window_readiness([match(1,"09:00")],RULES,[window(play_date="2026-10-25")])["ready"]
    assert not pitch_window_readiness([match(1,"09:00")],RULES,[window(confirmed=False)])["ready"]
    assert pitch_window_readiness([match(1,"09:00",None)],RULES,[])["issues"][0]["type"] == "missing_pitch"


@pytest.fixture
def cup_db(tmp_path,monkeypatch):
    path = tmp_path / "cup.sqlite"
    with sqlite3.connect(path) as con:
        con.executescript("""
        CREATE TABLE tournaments(id INTEGER PRIMARY KEY,name TEXT,start_date TEXT,end_date TEXT,tournament_date TEXT,schedule_dirty INTEGER,is_published INTEGER,arrangement_type TEXT,arena_address TEXT);
        INSERT INTO tournaments VALUES(46,'Slottskampen 2026','2026-10-24','2026-10-24','2026-10-24',1,0,'tournament','Örebro');
        CREATE TABLE schedule_rules(tournament_id INTEGER PRIMARY KEY,pitch_count INTEGER,first_match_time TEXT,latest_kickoff_time TEXT,halves INTEGER,minutes_per_half INTEGER,halftime_minutes INTEGER,pitch_break_minutes INTEGER,minimum_team_rest_minutes INTEGER,synchronized_pitch_times INTEGER DEFAULT 0,consider_pitch_travel INTEGER DEFAULT 0);
        INSERT INTO schedule_rules VALUES(46,1,'09:00','18:00',2,18,2,5,45,0,0);
        CREATE TABLE teams(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        INSERT INTO teams VALUES(1,46,'Örebro SK'),(2,46,'Bromölla');
        CREATE TABLE groups(id INTEGER PRIMARY KEY,tournament_id INTEGER,name TEXT);
        CREATE TABLE pitches(tournament_id INTEGER,pitch_number INTEGER,name TEXT,address TEXT,address_verified INTEGER DEFAULT 0,PRIMARY KEY(tournament_id,pitch_number));
        INSERT INTO pitches VALUES(46,1,'Sörbyvallen',NULL,0);
        CREATE TABLE pitch_day_windows(tournament_id INTEGER,pitch_number INTEGER,play_date TEXT,start_time TEXT,end_time TEXT,confirmed INTEGER,PRIMARY KEY(tournament_id,pitch_number,play_date));
        INSERT INTO pitch_day_windows VALUES(46,1,'2026-10-24','09:00','18:00',0);
        CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,home_source TEXT,away_source TEXT,scheduled_start TEXT,pitch_number INTEGER,stage TEXT,group_id INTEGER,round_no INTEGER,match_no INTEGER,schedule_published INTEGER DEFAULT 0);
        INSERT INTO matches VALUES(1,46,'team:1','team:2','2026-10-24T08:30',1,'Gruppspel',NULL,1,1,0);
        """)
    monkeypatch.delenv("TURSO_DATABASE_URL",raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN",raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH",str(path))
    for module in (schedule,venues,publication):
        monkeypatch.setattr(module,"_has_tournament_access",lambda *_:True)
    return path


def test_unconfirmed_to_approved_to_published_roundtrip_preserves_match(cup_db):
    before = schedule.admin_schedule(1,46)
    assert before["conflict_analysis"]["ok"]
    assert not before["pitch_window_readiness"]["ready"]
    with pytest.raises(ValueError,match="saknar bekräftad öppettid"):
        schedule.confirm_current_schedule(1,46)
    state = publication.admin_publication(1,46)
    assert not state["ready"]
    assert any("saknar bekräftad öppettid" in text for text in state["blockers"])
    assert not any("Öppna Schema och godkänn" in text for text in state["blockers"])
    with pytest.raises(ValueError):
        publication.set_publication(1,46,True)
    # Confirming the default start is insufficient; the first match starts earlier.
    venues.update_pitch_window(1,46,1,"2026-10-24",{"start_time":"09:00","end_time":"18:00","confirmed":True})
    with pytest.raises(ValueError,match="utanför planens bekräftade öppettid"):
        schedule.confirm_current_schedule(1,46)
    saved = venues.update_pitch_window(1,46,1,"2026-10-24",{"start_time":"08:30","end_time":"18:00","confirmed":True})
    assert saved["schedule_requirements"][0]["last_end"] == "2026-10-24T09:08:00"
    assert schedule.admin_schedule(1,46)["pitch_window_readiness"]["ready"]
    assert not publication.admin_publication(1,46)["ready"], "A plan confirmation still requires explicit schedule approval"
    confirmed = schedule.confirm_current_schedule(1,46)
    assert not confirmed["schedule_dirty"]
    assert confirmed["matches"][0]["scheduled_start"] == before["matches"][0]["scheduled_start"]
    assert publication.admin_publication(1,46)["ready"]
    assert publication.set_publication(1,46,True)["tournament"]["is_published"]


def test_access_denial_does_not_reveal_readiness(cup_db,monkeypatch):
    for module in (schedule,venues,publication):
        monkeypatch.setattr(module,"_has_tournament_access",lambda *_:False)
    assert schedule.admin_schedule(2,46) is None
    assert schedule.confirm_current_schedule(2,46) is None
    assert publication.admin_publication(2,46) is None
    assert venues.admin_venues(2,46) is None


def test_shortened_cup_returns_only_current_windows_and_preserves_old_dates(cup_db):
    with sqlite3.connect(cup_db) as con:
        con.execute("INSERT INTO pitch_day_windows VALUES(46,1,'2026-10-25','10:00','16:00',1)")
    payload = venues.admin_venues(1,46)
    assert payload['dates'] == ['2026-10-24']
    assert {row['play_date'] for row in payload['windows']} == {'2026-10-24'}
    assert payload['preserved_window_dates'] == ['2026-10-25']
    # The exact active editor payload can be saved without writing hidden days.
    for row in payload['windows']:
        venues.update_pitch_window(1,46,row['pitch_number'],row['play_date'],row)
    with sqlite3.connect(cup_db) as con:
        assert con.execute("SELECT start_time,end_time,confirmed FROM pitch_day_windows WHERE play_date='2026-10-25'").fetchone() == ('10:00','16:00',1)
        assert con.execute("SELECT scheduled_start FROM matches WHERE id=1").fetchone()[0] == '2026-10-24T08:30'
        con.execute("UPDATE tournaments SET end_date='2026-10-25' WHERE id=46")
    restored = venues.admin_venues(1,46)
    assert restored['preserved_window_dates'] == []
    assert next(row for row in restored['windows'] if row['play_date']=='2026-10-25')['start_time'] == '10:00'


def test_window_date_error_identifies_pitch_date_and_repair_step(cup_db):
    from cupnavi_api.venue_admin_routes import register_venue_admin_routes
    app = FastAPI()
    register_venue_admin_routes(app,lambda _: {'id':1})
    response = TestClient(app).put('/api/admin/cups/46/venues/pitches/1/windows/2026-10-25', json={'start_time':'08:00','end_time':'19:00'})
    assert response.status_code == 422
    detail = response.json()['detail']
    for text in ('Sörbyvallen','2026-10-25','Cupens datum är 2026-10-24','Cupinfo'):
        assert text in detail
    with sqlite3.connect(cup_db) as con:
        assert con.execute("SELECT COUNT(*) FROM pitch_day_windows WHERE play_date='2026-10-25'").fetchone()[0] == 0


def test_api_rejects_then_approves_then_publishes_with_same_readiness(cup_db):
    from cupnavi_api.venue_admin_routes import register_venue_admin_routes
    from cupnavi_api.publish_reporting_routes import register_publish_reporting_routes
    app = FastAPI()
    register_venue_admin_routes(app,lambda _: {"id":1})
    register_publish_reporting_routes(app,lambda _: {"id":1})
    client = TestClient(app)
    base = "/api/admin/cups/46"
    schedule_view = client.get(base+"/schedule").json()
    refusal = client.post(base+"/schedule/confirm")
    assert refusal.status_code == 422
    assert schedule_view["pitch_window_readiness"]["issues"][0]["message"] in refusal.json()["detail"]
    assert client.put(base+"/publication",json={"published":True}).status_code == 409
    response = client.put(base+"/venues/pitches/1/windows/2026-10-24",json={"intervals":[{"start_time":"08:30","end_time":"18:00"}],"confirmed":True})
    assert response.status_code == 200
    assert client.get(base+"/schedule").json()["pitch_window_readiness"]["ready"]
    response = client.post(base+"/schedule/confirm")
    assert response.status_code == 200
    assert response.json()["schedule_dirty"] is False
    assert client.get(base+"/publication").json()["ready"]
    response = client.put(base+"/publication",json={"published":True})
    assert response.status_code == 200
    assert response.json()["tournament"]["is_published"] == 1
