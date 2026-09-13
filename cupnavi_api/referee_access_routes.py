"""Narrow per-referee portal access for the Next app.

Each referee gets an individual four-digit code. Sessions are bound to both the
cup and referee and are invalidated immediately when that referee's code is
rotated. The portal is intentionally read-only: it exposes only the referee's
own assigned matches.
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


class RefereeLogin(BaseModel):
    cup: str
    referee_id: int
    code: str


def _table_columns(table: str) -> set[str]:
    with connect() as con:
        return {str(row[1]) for row in con.execute(f"PRAGMA table_info({table})").fetchall()}


def _referee_projection() -> str:
    columns = _table_columns("referees")
    fields = [field for field in ("id", "name", "active") if field in columns]
    return ",".join(fields)


def _referee(tournament_id: int, referee_id: int):
    projection = _referee_projection()
    if not projection or "id" not in projection or "name" not in projection:
        return None
    return one(
        f"SELECT {projection} FROM referees WHERE id=? AND tournament_id=?",
        (int(referee_id), int(tournament_id)),
    )


def _ensure_table():
    with connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS referee_portal_credentials (
                tournament_id INTEGER NOT NULL REFERENCES tournaments(id) ON DELETE CASCADE,
                referee_id INTEGER NOT NULL REFERENCES referees(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                PRIMARY KEY(tournament_id, referee_id)
            )"""
        )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def _credential(tournament_id: int, referee_id: int):
    _ensure_table()
    return one(
        """SELECT tournament_id,referee_id,code_salt,code_hash,created_at,rotated_at
           FROM referee_portal_credentials WHERE tournament_id=? AND referee_id=?""",
        (int(tournament_id), int(referee_id)),
    )


def referee_code_statuses(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    _ensure_table()
    projection = _referee_projection()
    if not projection:
        return {"referees": []}
    referees = all_rows(
        f"SELECT {projection} FROM referees WHERE tournament_id=? ORDER BY name,id",
        (int(tournament_id),),
    )
    credentials = {
        int(row["referee_id"]): row
        for row in all_rows(
            "SELECT referee_id,created_at,rotated_at FROM referee_portal_credentials WHERE tournament_id=?",
            (int(tournament_id),),
        )
    }
    return {
        "referees": [
            {
                "id": int(referee["id"]),
                "name": referee.get("name") or f"Domare {referee['id']}",
                "active": bool(referee.get("active", 1)),
                "code_active": int(referee["id"]) in credentials,
                "created_at": (credentials.get(int(referee["id"])) or {}).get("created_at"),
                "rotated_at": (credentials.get(int(referee["id"])) or {}).get("rotated_at"),
            }
            for referee in referees
        ]
    }


def rotate_referee_code(account_id: int, tournament_id: int, referee_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    referee = _referee(tournament_id, referee_id)
    if not referee:
        return None
    code = generate_short_numeric_code(4)
    salt, digest = new_code_hash(code)
    now = datetime.now().isoformat(timespec="seconds")
    _ensure_table()
    with connect() as con:
        existing = con.execute(
            "SELECT referee_id FROM referee_portal_credentials WHERE tournament_id=? AND referee_id=?",
            (int(tournament_id), int(referee_id)),
        ).fetchone()
        if existing:
            con.execute(
                """UPDATE referee_portal_credentials SET code_salt=?,code_hash=?,rotated_at=?
                   WHERE tournament_id=? AND referee_id=?""",
                (salt, digest, now, int(tournament_id), int(referee_id)),
            )
        else:
            con.execute(
                """INSERT INTO referee_portal_credentials
                   (tournament_id,referee_id,code_salt,code_hash,created_at,rotated_at)
                   VALUES(?,?,?,?,?,?)""",
                (int(tournament_id), int(referee_id), salt, digest, now, now),
            )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return {"code": code, "referee_id": int(referee_id), "name": referee.get("name"), "active": True, "rotated_at": now}


def _session_secret() -> bytes:
    secret = os.getenv("CUPNAVI_SESSION_SECRET") or os.getenv("TURSO_AUTH_TOKEN") or os.getenv("ADMIN_PASSWORD") or ""
    if not secret:
        raise RuntimeError("Referee sessions are not configured")
    return hashlib.sha256(("cupnavi-referee-session\0" + secret).encode("utf-8")).digest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _issue_session(tournament_id: int, referee_id: int, revision: str) -> str:
    now = int(time.time())
    payload = {"tid": int(tournament_id), "rid": int(referee_id), "role": "referee", "rev": revision, "iat": now, "exp": now + SESSION_TTL_SECONDS}
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
        if payload.get("role") != "referee" or int(payload.get("exp") or 0) <= int(time.time()):
            return None
        row = _credential(int(payload["tid"]), int(payload["rid"]))
        revision = str((row or {}).get("rotated_at") or (row or {}).get("created_at") or "")
        if not row or not hmac.compare_digest(str(payload.get("rev") or ""), revision):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError):
        return None


def _identity(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Domarinloggning krävs")
    payload = _verify_session(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(401, "Domarsessionen har gått ut eller är ogiltig")
    return payload


def _find_cup(value: str):
    text = str(value or "").strip()
    row = one(
        "SELECT id,name,public_slug FROM tournaments WHERE public_slug=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')",
        (text,),
    )
    if row:
        return row
    try:
        return one(
            "SELECT id,name,public_slug FROM tournaments WHERE id=? AND COALESCE(lifecycle_status,'draft') NOT IN ('trashed','purged')",
            (int(text),),
        )
    except (TypeError, ValueError):
        return None


def _assignments(tournament_id: int, referee_id: int):
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    referee = _referee(tournament_id, referee_id)
    if not tournament or not referee:
        return None
    match_columns = _table_columns("matches")
    match_column = "referee_id" if "referee_id" in match_columns else "assigned_referee_id" if "assigned_referee_id" in match_columns else None
    if not match_column:
        return {"referee": {"id": int(referee["id"]), "name": referee.get("name")}, "matches": []}
    resolver = tournament_participant_resolver(tournament)
    rows = all_rows(
        f"""SELECT id,stage,match_no,scheduled_start,pitch_number,home_source,away_source,home_score,away_score
            FROM matches WHERE tournament_id=? AND {match_column}=?
            ORDER BY CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,scheduled_start,id""",
        (int(tournament_id), int(referee_id)),
    )
    result = []
    for row in rows:
        home = resolver.resolve(row.get("home_source"))
        away = resolver.resolve(row.get("away_source"))
        item = dict(row)
        item["home_team"] = home.team_name if home.resolved else str(row.get("home_source") or "Ej avgjort")
        item["away_team"] = away.team_name if away.resolved else str(row.get("away_source") or "Ej avgjort")
        item["played"] = row.get("home_score") is not None and row.get("away_score") is not None
        result.append(item)
    return {"referee": {"id": int(referee["id"]), "name": referee.get("name")}, "matches": result}


def register_referee_access_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/role-codes/referees")
    def get_referee_codes(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = referee_code_statuses(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/role-codes/referees/{referee_id}/rotate")
    def post_referee_code(tournament_id: int, referee_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = rotate_referee_code(int(account["id"]), tournament_id, referee_id)
        if result is None:
            raise HTTPException(404, "Domare saknas eller åtkomst nekas")
        return result

    @app.post("/api/referee/session")
    def referee_login(payload: RefereeLogin, request: Request):
        cup = _find_cup(payload.cup)
        if not cup:
            raise HTTPException(401, "Fel cup, domare eller kod")
        referee = _referee(int(cup["id"]), int(payload.referee_id))
        if not referee or not bool(referee.get("active", 1)):
            raise HTTPException(401, "Fel cup, domare eller kod")
        subject = hashlib.sha256(f"{cup['id']}:{payload.referee_id}:{request.client.host if request.client else ''}".encode()).hexdigest()
        with connect() as con:
            allowed, retry_after, _ = consume_rate_limit(con, scope="referee_login", subject_hash=subject, limit=10, window_seconds=900)
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if not allowed:
            raise HTTPException(429, "För många kodförsök", headers={"Retry-After": str(retry_after)})
        credential = _credential(int(cup["id"]), int(payload.referee_id))
        if not credential or not verify_access_code(payload.code, credential["code_salt"], credential["code_hash"]):
            raise HTTPException(401, "Fel cup, domare eller kod")
        revision = str(credential.get("rotated_at") or credential.get("created_at") or "")
        return {"token": _issue_session(int(cup["id"]), int(payload.referee_id), revision), "cup": cup, "referee": {"id": int(referee["id"]), "name": referee.get("name")}}

    @app.get("/api/referee/session")
    def referee_session(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        cup = one("SELECT id,name,public_slug FROM tournaments WHERE id=?", (int(identity["tid"]),))
        referee = _referee(int(identity["tid"]), int(identity["rid"]))
        return {"cup": cup, "referee": {"id": int(referee["id"]), "name": referee.get("name")} if referee else None, "role": "referee"}

    @app.get("/api/referee/assignments")
    def referee_assignments(authorization: str | None = Header(default=None)):
        identity = _identity(authorization)
        result = _assignments(int(identity["tid"]), int(identity["rid"]))
        if result is None:
            raise HTTPException(404, "Domare eller cup saknas")
        return result
