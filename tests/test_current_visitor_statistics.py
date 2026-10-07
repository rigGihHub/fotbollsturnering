"""Real anonymous visit counting: persistence, cup boundaries and Swedish dates."""
import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from cupnavi_api import visitor_routes as visits


@pytest.fixture
def database(tmp_path, monkeypatch):
    path = tmp_path / "visits.db"
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(path))
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    with sqlite3.connect(path) as con:
        con.execute("CREATE TABLE tournaments(id INTEGER PRIMARY KEY,public_slug TEXT,is_published INTEGER)")
        con.executemany("INSERT INTO tournaments VALUES(?,?,?)", [(1,"slottskampen",1),(2,"other-cup",1),(3,"draft-cup",0)])
    return path


def moment(value="2026-10-07T12:00:00+00:00"):
    return datetime.fromisoformat(value)


def test_heartbeats_reloads_and_tabs_do_not_inflate_visitors(database):
    now=moment()
    first="a"*32
    assert visits.record_heartbeat("slottskampen",first,now=now)["active"]==1
    for seconds in (1,15,30):
        assert visits.record_heartbeat("1",first,now=now+timedelta(seconds=seconds))["active"]==1
    assert visits.record_heartbeat("slottskampen","b"*32,now=now+timedelta(seconds=30))["active"]==2
    stats=visits.visitor_statistics(1,now=now+timedelta(seconds=31))
    assert (stats["total"],stats["today"],stats["peak"],stats["active"])==(2,2,2,2)
    assert stats["days"]==[{"date":"2026-10-07","visitors":2,"peak":2}]
    assert visits.visitor_statistics(1,now=now+timedelta(seconds=120))["active"]==0
    assert visits.visitor_statistics(1,now=now+timedelta(seconds=120))["peak"]==2
    visits._ready_databases.clear()  # A restarted API keeps every persisted metric.
    assert visits.visitor_statistics(1,now=now)["total"]==2
    with sqlite3.connect(database) as con:
        stored=con.execute("SELECT visitor_hash FROM cup_visitors ORDER BY visitor_hash").fetchall()
    assert {row[0] for row in stored}=={hashlib.sha256(f"1:{token}".encode()).hexdigest() for token in (first,"b"*32)}


def test_swedish_midnight_counts_daily_unique_and_global_unique_separately(database):
    first=moment("2026-10-24T21:59:30+00:00")  # 23:59 Stockholm before DST change.
    second=first+timedelta(seconds=60)
    visits.record_heartbeat("1","a"*32,now=first)
    visits.record_heartbeat("1","a"*32,now=second)
    visits.record_heartbeat("1","b"*32,now=second)
    stats=visits.visitor_statistics(1,now=second)
    assert stats["total"]==2 and stats["today"]==2
    assert stats["days"]==[{"date":"2026-10-25","visitors":2,"peak":2},{"date":"2026-10-24","visitors":1,"peak":1}]
    later=visits.visitor_statistics(1,days=2,now=second+timedelta(days=3))
    assert later["total"]==2 and later["today"]==0 and later["peak"]==2
    # After the clock change, the same UTC time is still 23:00 the day before.
    assert later["days"]==[{"date":"2026-10-27","visitors":0,"peak":0},{"date":"2026-10-26","visitors":0,"peak":0}]
    assert stats["recorded_since"]==first.isoformat()


def test_counts_are_isolated_and_unpublished_cups_never_recorded(database):
    now=moment()
    assert visits.visitor_statistics(1,now=now)["recorded_since"] is None
    assert visits.visitor_statistics(1,now=now)["days"]==[]
    visits.record_heartbeat("1","a"*32,now=now)
    visits.record_heartbeat("other-cup","a"*32,now=now)
    assert visits.visitor_statistics(2,now=now)["total"]==1
    with pytest.raises(HTTPException) as caught:
        visits.record_heartbeat("draft-cup","a"*32,now=now)
    assert caught.value.status_code==404
    assert visits.visitor_statistics(3,now=now)["total"]==0
    with sqlite3.connect(database) as con:
        hashes=con.execute("SELECT visitor_hash FROM cup_visitors ORDER BY tournament_id").fetchall()
    assert hashes[0]!=hashes[1]


def test_simultaneous_first_visits_record_real_peak(database):
    now=moment()
    with ThreadPoolExecutor(max_workers=8) as pool:
        counts=list(pool.map(lambda index: visits.record_heartbeat("1",f"{index:032x}",now=now)["active"],range(24)))
    assert sorted(counts)==list(range(1,25))
    assert visits.visitor_statistics(1,now=now)["peak"]==24


def test_statistics_requires_admin_access_and_never_exposes_identifiers(database,monkeypatch):
    monkeypatch.setattr(visits,"admin_cupinfo",lambda account,cup:{"id":cup} if account==1 and cup==1 else None)
    def auth(header):
        if header!="Bearer organizer":raise HTTPException(401)
        return {"id":1}
    app=FastAPI()
    visits.register_visitor_routes(app,auth)
    client=TestClient(app)
    root="/api/admin/cups/1/visitors"
    assert client.get(root).status_code==401
    headers={"Authorization":"Bearer organizer"}
    assert client.get("/api/admin/cups/2/visitors",headers=headers).status_code==404
    assert client.get(root+"?days=0",headers=headers).status_code==422
    assert client.get(root+"?days=999999",headers=headers).status_code==422
    assert client.post("/api/public/cups/slottskampen/visitors/heartbeat",json={"visitor_id":"short"}).status_code==422
    assert client.post("/api/public/cups/draft-cup/visitors/heartbeat",json={"visitor_id":"a"*32}).status_code==404
    response=client.post("/api/public/cups/slottskampen/visitors/heartbeat",json={"visitor_id":"a"*32})
    assert response.json()["active"]==1 and response.headers["cache-control"]=="no-store"
    stats=client.get(root,headers=headers)
    assert stats.json()["total"]==1
    assert stats.headers["cache-control"]=="no-store"
    assert "visitor_hash" not in stats.text and "visitor_id" not in stats.text
