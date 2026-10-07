"""Cup-scoped anonymous browser counts, recorded separately from match reads."""
from __future__ import annotations

import hashlib
import os
import threading
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import Header, HTTPException, Query, Response
from pydantic import BaseModel, Field

from .admin_repository import admin_cupinfo
from .repository import _dict_rows, connect, backend_name

ACTIVE_WINDOW_SECONDS = 90
LOCAL_ZONE = ZoneInfo("Europe/Stockholm")
_schema_lock = threading.Lock()
_ready_databases: set[str] = set()


class VisitorHeartbeat(BaseModel):
    visitor_id: str = Field(min_length=32, max_length=64, pattern=r"^[a-zA-Z0-9_-]+$")


def _now():
    return datetime.now(timezone.utc)


def _ensure_schema():
    # Initialize once per database/process, never on a normal cup-page read.
    key = os.getenv("TURSO_DATABASE_URL", "") if backend_name() == "turso" else os.path.abspath(os.getenv("CUPNAVI_API_SQLITE_PATH", "turnering.db"))
    with _schema_lock:
        if key in _ready_databases:
            return
        with connect() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS cup_visitors (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                visitor_hash TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen INTEGER NOT NULL, last_day TEXT NOT NULL,
                PRIMARY KEY(tournament_id, visitor_hash))""")
            con.execute("CREATE INDEX IF NOT EXISTS idx_cup_visitors_active ON cup_visitors(tournament_id,last_seen)")
            con.execute("""CREATE TABLE IF NOT EXISTS cup_visitor_days (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                day TEXT NOT NULL, visitor_hash TEXT NOT NULL,
                PRIMARY KEY(tournament_id,day,visitor_hash))""")
            con.execute("""CREATE TABLE IF NOT EXISTS cup_visitor_daily_stats (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                day TEXT NOT NULL, recorded_since TEXT NOT NULL, peak INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY(tournament_id,day))""")
            # Count/day/peak updates run atomically inside the one heartbeat
            # statement. This avoids holding a remote write transaction across
            # multiple network round trips on every visitor's periodic signal.
            for event in ("INSERT", "UPDATE"):
                con.execute(f"""CREATE TRIGGER IF NOT EXISTS cup_visitors_after_{event.lower()}
                    AFTER {event} ON cup_visitors BEGIN
                    INSERT INTO cup_visitor_days(tournament_id,day,visitor_hash)
                        VALUES(NEW.tournament_id,NEW.last_day,NEW.visitor_hash)
                        ON CONFLICT(tournament_id,day,visitor_hash) DO NOTHING;
                    INSERT INTO cup_visitor_daily_stats(tournament_id,day,recorded_since,peak)
                        SELECT NEW.tournament_id,NEW.last_day,NEW.first_seen,COUNT(*) FROM cup_visitors
                        WHERE tournament_id=NEW.tournament_id AND last_seen>NEW.last_seen-{ACTIVE_WINDOW_SECONDS}
                        ON CONFLICT(tournament_id,day) DO UPDATE SET
                            peak=MAX(cup_visitor_daily_stats.peak,excluded.peak);
                    END""")
            con.commit()
        _ready_databases.add(key)


def _one(con, sql, params=()):
    rows = _dict_rows(con.execute(sql, params))
    return rows[0] if rows else None


def _published_id(con, public_key):
    try:
        numeric_id = int(public_key)
    except (ValueError, TypeError):
        numeric_id = -1
    row = _one(con, """SELECT id FROM tournaments WHERE is_published=1
        AND (public_slug=? OR id=?) ORDER BY CASE WHEN public_slug=? THEN 0 ELSE 1 END LIMIT 1""",
        (public_key, numeric_id, public_key))
    if not row:
        raise HTTPException(404, "Cupen är inte publicerad")
    return int(row["id"])


def record_heartbeat(public_key, visitor_id, *, now=None):
    _ensure_schema()
    now = now or _now()
    stamp = int(now.timestamp())
    day = now.astimezone(LOCAL_ZONE).date().isoformat()
    # No IP address, user-agent, referrer or raw browser identifier is stored.
    # Scope the digest to the cup to prevent cross-cup visitor linkage.
    with connect() as con:
        tid = _published_id(con, public_key)
        digest = hashlib.sha256(f"{tid}:{visitor_id}".encode()).hexdigest()
        active = _one(con, """INSERT INTO cup_visitors(tournament_id,visitor_hash,first_seen,last_seen,last_day)
            VALUES(?,?,?,?,?) ON CONFLICT(tournament_id,visitor_hash) DO UPDATE SET
            last_seen=excluded.last_seen,last_day=excluded.last_day
            WHERE cup_visitors.last_seen<excluded.last_seen
            RETURNING (SELECT COUNT(*) FROM cup_visitors WHERE tournament_id=? AND last_seen>?) AS n""",
            (tid,digest,now.isoformat(),stamp,day,tid,stamp-ACTIVE_WINDOW_SECONDS))
        if active is None:  # Same-second duplicate signal, e.g. two open tabs.
            active = _one(con, "SELECT COUNT(*) AS n FROM cup_visitors WHERE tournament_id=? AND last_seen>?", (tid,stamp-ACTIVE_WINDOW_SECONDS))
        con.commit()
    return {"active": int(active["n"]), "active_window_seconds": ACTIVE_WINDOW_SECONDS}


def visitor_statistics(tournament_id, *, days=30, now=None):
    _ensure_schema()
    now = now or _now()
    today = now.astimezone(LOCAL_ZONE).date()
    with connect() as con:
        totals = _one(con, """SELECT COUNT(*) AS total,
            SUM(CASE WHEN last_seen>? THEN 1 ELSE 0 END) AS active
            FROM cup_visitors WHERE tournament_id=?""", (int(now.timestamp())-ACTIVE_WINDOW_SECONDS,tournament_id))
        history = _one(con, "SELECT MIN(recorded_since) AS recorded_since,MAX(peak) AS peak FROM cup_visitor_daily_stats WHERE tournament_id=?", (tournament_id,))
        today_count = _one(con, "SELECT COUNT(*) AS n FROM cup_visitor_days WHERE tournament_id=? AND day=?", (tournament_id,today.isoformat()))
        rows = _dict_rows(con.execute("""SELECT d.day AS date,d.peak,
            (SELECT COUNT(*) FROM cup_visitor_days v WHERE v.tournament_id=d.tournament_id AND v.day=d.day) AS visitors
            FROM cup_visitor_daily_stats d WHERE d.tournament_id=? AND d.day>=? AND d.day<=? ORDER BY d.day DESC""",
            (tournament_id,(today-timedelta(days=days-1)).isoformat(),today.isoformat())))
    recorded_since = history["recorded_since"]
    daily = []
    if recorded_since:
        start = max(datetime.fromisoformat(recorded_since).astimezone(LOCAL_ZONE).date(), today-timedelta(days=days-1))
        by_date = {row["date"]: row for row in rows}
        cursor = today
        while cursor >= start:
            daily.append(by_date.get(cursor.isoformat(), {"date":cursor.isoformat(),"visitors":0,"peak":0}))
            cursor -= timedelta(days=1)
    return {"total":int(totals["total"] or 0), "today":int(today_count["n"]),
        "active":int(totals["active"] or 0), "peak":int(history["peak"] or 0),
        "recorded_since":recorded_since, "timezone":"Europe/Stockholm",
        "active_window_seconds":ACTIVE_WINDOW_SECONDS, "days":daily}


def register_visitor_routes(app, admin_identity):
    @app.post("/api/public/cups/{public_key}/visitors/heartbeat")
    def heartbeat(public_key: str, payload: VisitorHeartbeat, response: Response):
        response.headers["Cache-Control"] = "no-store"
        return record_heartbeat(public_key, payload.visitor_id)

    @app.get("/api/admin/cups/{tournament_id}/visitors")
    def statistics(tournament_id: int, response: Response, days: int = Query(default=30,ge=1,le=3660), authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        if not admin_cupinfo(int(account["id"]), tournament_id):
            raise HTTPException(404, "Cup saknas eller åtkomst nekas")
        response.headers["Cache-Control"] = "no-store"
        return visitor_statistics(tournament_id, days=days)
