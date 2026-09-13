"""Per-team portal access for team leaders.

Each team gets an individual four-digit code. Sessions are scoped to one cup
and one team. The portal is intentionally read-only in this first parity step:
it exposes only the team's own roster and matches plus basic cup information.
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
from cupnavi_core.team_portal import generate_short_numeric_code, new_code_hash, verify_access_code
from .admin_repository import _has_tournament_access
from .participant_resolution_repository import tournament_participant_resolver
from .repository import all_rows, connect, one

SESSION_TTL_SECONDS = 60 * 60 * 8


class TeamLogin(BaseModel):
    cup: str
    team_id: int
    code: str


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
    return {
        "teams": [
            {
                **team,
                "code_active": int(team["id"]) in credentials,
                "created_at": (credentials.get(int(team["id"])) or {}).get("created_at"),
                "rotated_at": (credentials.get(int(team["id"])) or {}).get("rotated_at"),
            }
            for team in teams
        ]
    }


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
    return {"cup": cup, "team": team, "players": players, "matches": matches}


def register_team_access_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/role-codes/teams")
    def get_team_codes(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = team_code_statuses(int(account["id"]), tournament_id)
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
