"""Per-team portal access for team leaders.

Each team gets an individual four-digit code and a session scoped to one cup and
one team. The portal exposes only the team's own roster and matches. Team leaders
may maintain their roster until the configured deadline, confirm it, and check
in the team. Every write is recorded in a small audit trail.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from datetime import datetime

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel

from cupnavi_core.rate_limit import consume_rate_limit
from cupnavi_core.team_portal import (
    generate_short_numeric_code,
    new_code_hash,
    squad_deadline_at,
    squad_is_locked,
    verify_access_code,
)
from .admin_repository import _has_tournament_access
from .participant_resolution_repository import tournament_participant_resolver
from .repository import all_rows, connect, one

SESSION_TTL_SECONDS = 60 * 60 * 8


class TeamLogin(BaseModel):
    cup: str
    team_id: int
    code: str


class TeamPlayerWrite(BaseModel):
    name: str | None = None
    player_number: int | None = None


class TeamPortalSettingsWrite(BaseModel):
    checkin_enabled: bool | None = None
    roster_edit_enabled: bool | None = None
    deadline_minutes_before_first_match: int | None = None


def _model_values(model):
    dump = getattr(model, "model_dump", None)
    return dump(exclude_unset=True) if callable(dump) else model.dict(exclude_unset=True)


def _ensure_table():
    with connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS team_portal_credentials (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                PRIMARY KEY(tournament_id, team_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS team_portal_settings (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                checkin_enabled INTEGER NOT NULL DEFAULT 1,
                roster_edit_enabled INTEGER NOT NULL DEFAULT 1,
                deadline_minutes_before_first_match INTEGER NOT NULL DEFAULT 60,
                updated_at TEXT NOT NULL
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS team_portal_state (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                team_id INTEGER NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
                roster_confirmed_at TEXT,
                checked_in_at TEXT,
                updated_at TEXT NOT NULL,
                PRIMARY KEY(tournament_id, team_id)
            )"""
        )
        con.execute(
            """CREATE TABLE IF NOT EXISTS team_portal_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tournament_id INTEGER NOT NULL,
                team_id INTEGER NOT NULL,
                event TEXT NOT NULL,
                details TEXT,
                created_at TEXT NOT NULL
            )"""
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def _credential(tournament_id: int, team_id: int):
    _ensure_table()
    return one(
        """SELECT tournament_id,team_id,code_salt,code_hash,created_at,rotated_at
           FROM team_portal_credentials WHERE tournament_id=? AND team_id=?""",
        (int(tournament_id), int(team_id)),
    )


def _team(tournament_id: int, team_id: int):
    return one(
        "SELECT id,name,age_class,group_id FROM teams WHERE id=? AND tournament_id=?",
        (int(team_id), int(tournament_id)),
    )


def _settings(tournament_id: int):
    _ensure_table()
    row = one(
        """SELECT checkin_enabled,roster_edit_enabled,deadline_minutes_before_first_match,updated_at
           FROM team_portal_settings WHERE tournament_id=?""",
        (int(tournament_id),),
    )
    return {
        "checkin_enabled": bool((row or {}).get("checkin_enabled", 1)),
        "roster_edit_enabled": bool((row or {}).get("roster_edit_enabled", 1)),
        "deadline_minutes_before_first_match": int((row or {}).get("deadline_minutes_before_first_match", 60) or 0),
        "updated_at": (row or {}).get("updated_at"),
    }


def _state(tournament_id: int, team_id: int):
    _ensure_table()
    row = one(
        """SELECT roster_confirmed_at,checked_in_at,updated_at
           FROM team_portal_state WHERE tournament_id=? AND team_id=?""",
        (int(tournament_id), int(team_id)),
    )
    return {
        "roster_confirmed_at": (row or {}).get("roster_confirmed_at"),
        "checked_in_at": (row or {}).get("checked_in_at"),
        "updated_at": (row or {}).get("updated_at"),
    }


def _upsert_state(tournament_id: int, team_id: int, *, roster_confirmed_at=None, checked_in_at=None):
    current = _state(tournament_id, team_id)
    now = datetime.now().isoformat(timespec="seconds")
    confirmed = current.get("roster_confirmed_at") if roster_confirmed_at is None else roster_confirmed_at
    checked = current.get("checked_in_at") if checked_in_at is None else checked_in_at
    with connect() as con:
        existing = con.execute(
            "SELECT team_id FROM team_portal_state WHERE tournament_id=? AND team_id=?",
            (int(tournament_id), int(team_id)),
        ).fetchone()
        if existing:
            con.execute(
                """UPDATE team_portal_state SET roster_confirmed_at=?,checked_in_at=?,updated_at=?
                   WHERE tournament_id=? AND team_id=?""",
                (confirmed, checked, now, int(tournament_id), int(team_id)),
            )
        else:
            con.execute(
                """INSERT INTO team_portal_state
                   (tournament_id,team_id,roster_confirmed_at,checked_in_at,updated_at)
                   VALUES(?,?,?,?,?)""",
                (int(tournament_id), int(team_id), confirmed, checked, now),
            )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _state(tournament_id, team_id)


def _audit(tournament_id: int, team_id: int, event: str, details: dict | None = None):
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as con:
        con.execute(
            "INSERT INTO team_portal_audit(tournament_id,team_id,event,details,created_at) VALUES(?,?,?,?,?)",
            (int(tournament_id), int(team_id), str(event), json.dumps(details or {}, ensure_ascii=False, sort_keys=True), now),
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def _first_team_start(tournament_id: int, team_id: int, tournament: dict | None = None):
    tournament = tournament or one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    resolver = tournament_participant_resolver(tournament)
    rows = all_rows(
        """SELECT scheduled_start,home_source,away_source FROM matches
           WHERE tournament_id=? AND schedule_published=1 AND scheduled_start IS NOT NULL
           ORDER BY scheduled_start,id""",
        (int(tournament_id),),
    )
    for row in rows:
        home = resolver.resolve(row.get("home_source"))
        away = resolver.resolve(row.get("away_source"))
        if home.team_id == int(team_id) or away.team_id == int(team_id):
            return row.get("scheduled_start")
    return None


def _workflow(tournament_id: int, team_id: int, tournament: dict | None = None):
    settings = _settings(tournament_id)
    state = _state(tournament_id, team_id)
    first_start = _first_team_start(tournament_id, team_id, tournament)
    deadline = squad_deadline_at(first_start, settings["deadline_minutes_before_first_match"]) if first_start else None
    deadline_locked = squad_is_locked(first_start, settings["deadline_minutes_before_first_match"]) if first_start else False
    roster_locked = bool(state.get("roster_confirmed_at")) or deadline_locked or not settings["roster_edit_enabled"]
    return {
        "settings": settings,
        "state": state,
        "first_match_start": first_start,
        "roster_deadline": deadline.isoformat(timespec="minutes") if deadline else None,
        "deadline_locked": deadline_locked,
        "roster_locked": roster_locked,
        "can_edit_roster": not roster_locked,
        "can_confirm_roster": not bool(state.get("roster_confirmed_at")) and not deadline_locked,
        "can_check_in": settings["checkin_enabled"] and not bool(state.get("checked_in_at")),
    }


def team_code_statuses(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    _ensure_table()
    teams = all_rows(
        "SELECT id,name,age_class FROM teams WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    credentials = {
        int(row["team_id"]): row
        for row in all_rows(
            "SELECT team_id,created_at,rotated_at FROM team_portal_credentials WHERE tournament_id=?",
            (int(tournament_id),),
        )
    }
    states = {
        int(row["team_id"]): row
        for row in all_rows(
            "SELECT team_id,roster_confirmed_at,checked_in_at FROM team_portal_state WHERE tournament_id=?",
            (int(tournament_id),),
        )
    }
    return {
        "settings": _settings(tournament_id),
        "teams": [
            {
                **team,
                "code_active": int(team["id"]) in credentials,
                "created_at": (credentials.get(int(team["id"])) or {}).get("created_at"),
                "rotated_at": (credentials.get(int(team["id"])) or {}).get("rotated_at"),
                "roster_confirmed_at": (states.get(int(team["id"])) or {}).get("roster_confirmed_at"),
                "checked_in_at": (states.get(int(team["id"])) or {}).get("checked_in_at"),
            }
            for team in teams
        ],
    }


def update_team_portal_settings(account_id: int, tournament_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    current = _settings(tournament_id)
    enabled = bool(values.get("checkin_enabled", current["checkin_enabled"]))
    edit_enabled = bool(values.get("roster_edit_enabled", current["roster_edit_enabled"]))
    minutes = int(values.get("deadline_minutes_before_first_match", current["deadline_minutes_before_first_match"]))
    if minutes < 0 or minutes > 10080:
        raise ValueError("Truppdeadline måste vara mellan 0 och 10080 minuter")
    now = datetime.now().isoformat(timespec="seconds")
    with connect() as con:
        existing = con.execute("SELECT tournament_id FROM team_portal_settings WHERE tournament_id=?", (int(tournament_id),)).fetchone()
        if existing:
            con.execute(
                """UPDATE team_portal_settings SET checkin_enabled=?,roster_edit_enabled=?,deadline_minutes_before_first_match=?,updated_at=?
                   WHERE tournament_id=?""",
                (1 if enabled else 0, 1 if edit_enabled else 0, minutes, now, int(tournament_id)),
            )
        else:
            con.execute(
                """INSERT INTO team_portal_settings
                   (tournament_id,checkin_enabled,roster_edit_enabled,deadline_minutes_before_first_match,updated_at)
                   VALUES(?,?,?,?,?)""",
                (int(tournament_id), 1 if enabled else 0, 1 if edit_enabled else 0, minutes, now),
            )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return _settings(tournament_id)


def rotate_team_code(account_id: int, tournament_id: int, team_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    team = _team(tournament_id, team_id)
    if not team:
        return None
    code = generate_short_numeric_code(4)
    salt, digest = new_code_hash(code)
    now = datetime.now().isoformat(timespec="seconds")
    _ensure_table()
    with connect() as con:
        existing = con.execute(
            "SELECT team_id FROM team_portal_credentials WHERE tournament_id=? AND team_id=?",
            (int(tournament_id), int(team_id)),
        ).fetchone()
        if existing:
            con.execute(
                """UPDATE team_portal_credentials SET code_salt=?,code_hash=?,rotated_at=?
                   WHERE tournament_id=? AND team_id=?""",
                (salt, digest, now, int(tournament_id), int(team_id)),
            )
        else:
            con.execute(
                """INSERT INTO team_portal_credentials
                   (tournament_id,team_id,code_salt,code_hash,created_at,rotated_at)
                   VALUES(?,?,?,?,?,?)""",
                (int(tournament_id), int(team_id), salt, digest, now, now),
            )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return {"code": code, "team_id": int(team_id), "name": team.get("name"), "rotated_at": now}


def _session_secret() -> bytes:
    secret = os.getenv("CUPNAVI_SESSION_SECRET") or os.getenv("TURSO_AUTH_TOKEN") or os.getenv("ADMIN_PASSWORD") or ""
    if not secret:
        raise RuntimeError("Team sessions are not configured")
    return hashlib.sha256(("cupnavi-team-session\0" + secret).encode("utf-8")).digest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _issue_session(tournament_id: int, team_id: int, revision: str) -> str:
    now = int(time.time())
    payload = {"tid": int(tournament_id), "team_id": int(team_id), "role": "team", "rev": revision, "iat": now, "exp": now + SESSION_TTL_SECONDS}
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64e(hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def _verify_session(token: str):
    try:
        body, supplied = str(token or "").split(".", 1)
        expected = _b64e(hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied, expected):
            return None
        payload = json.loads(_b64d(body).decode("utf-8"))
        if payload.get("role") != "team" or int(payload.get("exp") or 0) <= int(time.time()):
            return None
        row = _credential(int(payload["tid"]), int(payload["team_id"]))
        revision = str((row or {}).get("rotated_at") or (row or {}).get("created_at") or "")
        if not row or not hmac.compare_digest(str(payload.get("rev") or ""), revision):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError):
        return None


def _identity(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Laginloggning krävs")
    payload = _verify_session(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(401, "Lagsessionen har gått ut eller är ogiltig")
    return payload


def _find_cup(value: str):
    text = str(value or "").strip()
    row = one(
        "SELECT id,name,public_slug,start_date,end_date,arena_address,public_information FROM tournaments WHERE public_slug=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')",
        (text,),
    )
    if row:
        return row
    try:
        return one(
            "SELECT id,name,public_slug,start_date,end_date,arena_address,public_information FROM tournaments WHERE id=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')",
            (int(text),),
        )
    except (TypeError, ValueError):
        return None


def _team_portal_payload(tournament_id: int, team_id: int):
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    team = _team(tournament_id, team_id)
    if not tournament or not team:
        return None
    players = all_rows(
        "SELECT id,name,player_number FROM players WHERE team_id=? ORDER BY CASE WHEN player_number IS NULL THEN 1 ELSE 0 END,player_number,name,id",
        (int(team_id),),
    )
    resolver = tournament_participant_resolver(tournament)
    rows = all_rows(
        """SELECT id,stage,match_no,scheduled_start,pitch_number,home_source,away_source,home_score,away_score,schedule_published
           FROM matches WHERE tournament_id=? AND schedule_published=1
           ORDER BY CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,scheduled_start,id""",
        (int(tournament_id),),
    )
    matches = []
    for row in rows:
        home = resolver.resolve(row.get("home_source"))
        away = resolver.resolve(row.get("away_source"))
        if home.team_id != int(team_id) and away.team_id != int(team_id):
            continue
        item = dict(row)
        item["home_team"] = home.team_name if home.resolved else str(row.get("home_source") or "Ej avgjort")
        item["away_team"] = away.team_name if away.resolved else str(row.get("away_source") or "Ej avgjort")
        item["played"] = row.get("home_score") is not None and row.get("away_score") is not None
        matches.append(item)
    cup = {key: tournament.get(key) for key in ("id", "name", "public_slug", "start_date", "end_date", "arena_address", "public_information")}
    return {"cup": cup, "team": team, "players": players, "matches": matches, "workflow": _workflow(tournament_id, team_id, tournament)}


def _require_roster_write(identity: dict):
    tournament_id = int(identity["tid"])
    team_id = int(identity["team_id"])
    workflow = _workflow(tournament_id, team_id)
    if not workflow["settings"]["roster_edit_enabled"]:
        raise HTTPException(403, "Cupadministratören har stängt truppredigering")
    if workflow["state"].get("roster_confirmed_at"):
        raise HTTPException(409, "Truppen är redan bekräftad och låst")
    if workflow["deadline_locked"]:
        raise HTTPException(409, "Truppdeadlinen har passerat")
    return tournament_id, team_id


def _player_values(values: dict):
    name = str(values.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "Spelarnamn krävs")
    raw = values.get("player_number")
    number = None if raw in (None, "") else int(raw)
    if number is not None and (number < 0 or number > 999):
        raise HTTPException(422, "Tröjnummer måste vara mellan 0 och 999")
    return name, number


def register_team_access_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/role-codes/teams")
    def get_team_codes(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = team_code_statuses(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/team-portal-settings")
    def put_team_portal_settings(tournament_id: int, payload: TeamPortalSettingsWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            result = update_team_portal_settings(int(account["id"]), tournament_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/role-codes/teams/{team_id}/rotate")
    def post_team_code(tournament_id: int, team_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = rotate_team_code(int(account["id"]), tournament_id, team_id)
        if result is None:
            raise HTTPException(404, "Lag saknas eller åtkomst nekas")
        return result

    @app.post("/api/team/session")
    def team_login(payload: TeamLogin, request: Request):
        cup = _find_cup(payload.cup)
        if not cup or not _team(int(cup["id"]), int(payload.team_id)):
            raise HTTPException(401, "Fel cup, lag eller kod")
        subject = hashlib.sha256(f"{cup['id']}:{payload.team_id}:{request.client.host if request.client else ''}".encode()).hexdigest()
        with connect() as con:
            allowed, retry_after, _ = consume_rate_limit(con, scope="team_login", subject_hash=subject, limit=10, window_seconds=900)
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if not allowed:
            raise HTTPException(429, "För många kodförsök", headers={"Retry-After": str(retry_after)})
        credential = _credential(int(cup["id"]), int(payload.team_id))
        if not credential or not verify_access_code(payload.code, credential["code_salt"], credential["code_hash"]):
            raise HTTPException(401, "Fel cup, lag eller kod")
        revision = str(credential.get("rotated_at") or credential.get("created_at") or "")
        team = _team(int(cup["id"]), int(payload.team_id))
        return {"token": _issue_session(int(cup["id"]), int(payload.team_id), revision), "cup": cup, "team": team}

    @app.get("/api/team/session")
    def team_session(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        payload = _team_portal_payload(int(identity["tid"]), int(identity["team_id"]))
        if payload is None:
            raise HTTPException(404, "Lag eller cup saknas")
        return {"cup": payload["cup"], "team": payload["team"], "role": "team"}

    @app.get("/api/team/portal")
    def team_portal(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        payload = _team_portal_payload(int(identity["tid"]), int(identity["team_id"]))
        if payload is None:
            raise HTTPException(404, "Lag eller cup saknas")
        return payload

    @app.post("/api/team/players", status_code=201)
    def team_add_player(payload: TeamPlayerWrite, authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        tournament_id, team_id = _require_roster_write(identity)
        name, number = _player_values(_model_values(payload))
        with connect() as con:
            cur = con.execute("INSERT INTO players(team_id,name,player_number) VALUES(?,?,?)", (team_id, name, number))
            player_id = int(cur.lastrowid)
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        _audit(tournament_id, team_id, "player_added", {"player_id": player_id, "name": name, "player_number": number})
        return one("SELECT id,name,player_number FROM players WHERE id=? AND team_id=?", (player_id, team_id))

    @app.put("/api/team/players/{player_id}")
    def team_update_player(player_id: int, payload: TeamPlayerWrite, authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        tournament_id, team_id = _require_roster_write(identity)
        current = one("SELECT id,name,player_number FROM players WHERE id=? AND team_id=?", (int(player_id), team_id))
        if not current:
            raise HTTPException(404, "Spelaren finns inte i ditt lag")
        values = _model_values(payload)
        name = str(values.get("name", current.get("name")) or "").strip()
        if not name:
            raise HTTPException(422, "Spelarnamn krävs")
        raw = values.get("player_number", current.get("player_number"))
        number = None if raw in (None, "") else int(raw)
        if number is not None and (number < 0 or number > 999):
            raise HTTPException(422, "Tröjnummer måste vara mellan 0 och 999")
        with connect() as con:
            con.execute("UPDATE players SET name=?,player_number=? WHERE id=? AND team_id=?", (name, number, int(player_id), team_id))
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        _audit(tournament_id, team_id, "player_updated", {"player_id": int(player_id), "before": current, "after": {"name": name, "player_number": number}})
        return one("SELECT id,name,player_number FROM players WHERE id=? AND team_id=?", (int(player_id), team_id))

    @app.delete("/api/team/players/{player_id}")
    def team_delete_player(player_id: int, authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        tournament_id, team_id = _require_roster_write(identity)
        current = one("SELECT id,name,player_number FROM players WHERE id=? AND team_id=?", (int(player_id), team_id))
        if not current:
            raise HTTPException(404, "Spelaren finns inte i ditt lag")
        used = one("SELECT COUNT(*) AS n FROM player_match_stats WHERE player_id=?", (int(player_id),))
        if used and int(used.get("n") or 0) > 0:
            raise HTTPException(409, "Spelaren har registrerade matchhändelser och kan inte tas bort")
        with connect() as con:
            con.execute("DELETE FROM players WHERE id=? AND team_id=?", (int(player_id), team_id))
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        _audit(tournament_id, team_id, "player_deleted", current)
        return {"deleted": True, "player": current}

    @app.post("/api/team/roster/confirm")
    def team_confirm_roster(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        tournament_id = int(identity["tid"])
        team_id = int(identity["team_id"])
        workflow = _workflow(tournament_id, team_id)
        if workflow["state"].get("roster_confirmed_at"):
            return workflow["state"]
        if workflow["deadline_locked"]:
            raise HTTPException(409, "Truppdeadlinen har passerat")
        count = one("SELECT COUNT(*) AS n FROM players WHERE team_id=?", (team_id,))
        now = datetime.now().isoformat(timespec="seconds")
        state = _upsert_state(tournament_id, team_id, roster_confirmed_at=now)
        _audit(tournament_id, team_id, "roster_confirmed", {"player_count": int((count or {}).get("n") or 0)})
        return state

    @app.post("/api/team/check-in")
    def team_check_in(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        tournament_id = int(identity["tid"])
        team_id = int(identity["team_id"])
        workflow = _workflow(tournament_id, team_id)
        if not workflow["settings"]["checkin_enabled"]:
            raise HTTPException(403, "Cupadministratören har stängt lagincheckning")
        if workflow["state"].get("checked_in_at"):
            return workflow["state"]
        now = datetime.now().isoformat(timespec="seconds")
        state = _upsert_state(tournament_id, team_id, checked_in_at=now)
        _audit(tournament_id, team_id, "team_checked_in", {})
        return state
