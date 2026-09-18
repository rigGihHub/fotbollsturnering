"""Tournament-scoped role codes and narrow match-reporter sessions for Next admin."""
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
from .admin_auth import OWNER_ACCOUNT_ID
from .admin_repository import _has_tournament_access
from .match_events_admin_repository import admin_event_matches, admin_match_events, update_player_match_events
from .publish_reporting_repository import admin_reporting, save_result, set_reporter_match_status
from .repository import connect, one

SESSION_TTL_SECONDS = 60 * 60 * 48


class ReporterLogin(BaseModel):
    cup: str
    code: str


class ReporterCodeRotate(BaseModel):
    valid_hours: int = 48


class ReporterResultWrite(BaseModel):
    home_score: int
    away_score: int
    home_penalties: int | None = None
    away_penalties: int | None = None
    expected_home_score: int | None = None
    expected_away_score: int | None = None
    expected_home_penalties: int | None = None
    expected_away_penalties: int | None = None


class EventCounters(BaseModel):
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0


class ReporterEventWrite(BaseModel):
    goals: int = 0
    assists: int = 0
    yellow_cards: int = 0
    red_cards: int = 0
    expected: EventCounters


class ReporterStatusWrite(BaseModel):
    status: str
    expected_status: str


def _model_values(model):
    dump = getattr(model, "model_dump", None)
    return dump() if callable(dump) else model.dict()


def _ensure_reporter_table():
    with connect() as con:
        con.execute(
            """CREATE TABLE IF NOT EXISTS match_reporter_credentials (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                valid_hours INTEGER NOT NULL DEFAULT 48
            )"""
        )
        columns = {str(row[1]) for row in con.execute("PRAGMA table_info(match_reporter_credentials)").fetchall()}
        if "valid_hours" not in columns:
            con.execute("ALTER TABLE match_reporter_credentials ADD COLUMN valid_hours INTEGER NOT NULL DEFAULT 48")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()


def _credential(tournament_id: int):
    _ensure_reporter_table()
    return one(
        "SELECT tournament_id,code_salt,code_hash,created_at,rotated_at,valid_hours FROM match_reporter_credentials WHERE tournament_id=?",
        (int(tournament_id),),
    )


def reporter_code_status(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    row = _credential(tournament_id)
    return {
        "active": bool(row),
        "created_at": row.get("created_at") if row else None,
        "rotated_at": row.get("rotated_at") if row else None,
        "valid_hours": int(row.get("valid_hours") or 48) if row else 48,
    }


def rotate_reporter_code(account_id: int, tournament_id: int, valid_hours: int = 48):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    valid_hours = max(1, min(168, int(valid_hours)))
    code = generate_short_numeric_code(4)
    salt, digest = new_code_hash(code)
    now = datetime.now().isoformat(timespec="seconds")
    _ensure_reporter_table()
    with connect() as con:
        existing = con.execute(
            "SELECT tournament_id FROM match_reporter_credentials WHERE tournament_id=?",
            (int(tournament_id),),
        ).fetchone()
        if existing:
            con.execute(
                "UPDATE match_reporter_credentials SET code_salt=?,code_hash=?,rotated_at=?,valid_hours=? WHERE tournament_id=?",
                (salt, digest, now, valid_hours, int(tournament_id)),
            )
        else:
            con.execute(
                "INSERT INTO match_reporter_credentials(tournament_id,code_salt,code_hash,created_at,rotated_at,valid_hours) VALUES(?,?,?,?,?,?)",
                (int(tournament_id), salt, digest, now, now, valid_hours),
            )
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return {"code": code, **reporter_code_status(account_id, tournament_id)}


def _session_secret() -> bytes:
    secret = os.getenv("CUPNAVI_SESSION_SECRET") or os.getenv("TURSO_AUTH_TOKEN") or os.getenv("ADMIN_PASSWORD") or ""
    if not secret:
        raise RuntimeError("Reporter sessions are not configured")
    return hashlib.sha256(("cupnavi-reporter-session\0" + secret).encode("utf-8")).digest()


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64d(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _issue_reporter_session(tournament_id: int, revision: str, valid_hours: int = 48) -> str:
    now = int(time.time())
    payload = {"tid": int(tournament_id), "role": "reporter", "rev": revision, "iat": now, "exp": now + min(SESSION_TTL_SECONDS, max(1, int(valid_hours)) * 60 * 60)}
    body = _b64e(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
    sig = _b64e(hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
    return f"{body}.{sig}"


def _verify_reporter_session(token: str):
    try:
        body, supplied = str(token or "").split(".", 1)
        expected = _b64e(hmac.new(_session_secret(), body.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(supplied, expected):
            return None
        payload = json.loads(_b64d(body).decode("utf-8"))
        if payload.get("role") != "reporter" or int(payload.get("exp") or 0) <= int(time.time()):
            return None
        row = _credential(int(payload["tid"]))
        revision = str((row or {}).get("rotated_at") or (row or {}).get("created_at") or "")
        if not row or not hmac.compare_digest(str(payload.get("rev") or ""), revision):
            return None
        return payload
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, RuntimeError):
        return None


def _reporter_identity(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Reporter authentication required")
    payload = _verify_reporter_session(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(401, "Reporter session expired or invalid")
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


def _reporter_match_in_cup(tournament_id: int, match_id: int) -> bool:
    return bool(one("SELECT 1 AS ok FROM matches WHERE id=? AND tournament_id=?", (int(match_id), int(tournament_id))))


def _require_reporter_match(tournament_id: int, match_id: int):
    if not _reporter_match_in_cup(tournament_id, match_id):
        raise HTTPException(404, "Match saknas eller tillhör en annan cup")


def register_role_access_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/role-codes/reporter")
    def get_reporter_code_status(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = reporter_code_status(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/role-codes/reporter/rotate")
    def post_rotate_reporter_code(tournament_id: int, payload: ReporterCodeRotate, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = rotate_reporter_code(int(account["id"]), tournament_id, payload.valid_hours)
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.post("/api/reporter/session")
    def reporter_login(payload: ReporterLogin, request: Request):
        cup = _find_cup(payload.cup)
        if not cup:
            raise HTTPException(401, "Fel cup eller kod")
        subject = hashlib.sha256(f"{cup['id']}:{request.client.host if request.client else ''}".encode()).hexdigest()
        with connect() as con:
            allowed, retry_after, _ = consume_rate_limit(con, scope="reporter_login", subject_hash=subject, limit=10, window_seconds=900)
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if not allowed:
            raise HTTPException(429, "För många kodförsök", headers={"Retry-After": str(retry_after)})
        credential = _credential(int(cup["id"]))
        if not credential or not verify_access_code(payload.code, credential["code_salt"], credential["code_hash"]):
            raise HTTPException(401, "Fel cup eller kod")
        revision = str(credential.get("rotated_at") or credential.get("created_at") or "")
        return {"token": _issue_reporter_session(int(cup["id"]), revision, int(credential.get("valid_hours") or 48)), "cup": cup, "role": "reporter"}

    @app.get("/api/reporter/session")
    def reporter_session(authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        cup = one("SELECT id,name,public_slug FROM tournaments WHERE id=?", (int(identity["tid"]),))
        return {"cup": cup, "role": "reporter"}

    @app.get("/api/reporter/reporting")
    def reporter_reporting(authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        return admin_reporting(OWNER_ACCOUNT_ID, int(identity["tid"]))

    @app.put("/api/reporter/reporting/matches/{match_id}")
    def reporter_put_result(match_id: int, payload: ReporterResultWrite, authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        _require_reporter_match(int(identity["tid"]), match_id)
        try:
            return save_result(
                OWNER_ACCOUNT_ID, int(identity["tid"]), match_id,
                payload.home_score, payload.away_score,
                payload.expected_home_score, payload.expected_away_score,
                home_penalties=payload.home_penalties, away_penalties=payload.away_penalties,
                expected_home_penalties=payload.expected_home_penalties,
                expected_away_penalties=payload.expected_away_penalties,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.put("/api/reporter/reporting/matches/{match_id}/status")
    def reporter_put_status(match_id: int, payload: ReporterStatusWrite, authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        _require_reporter_match(int(identity["tid"]), match_id)
        try:
            result = set_reporter_match_status(
                OWNER_ACCOUNT_ID,
                int(identity["tid"]),
                match_id,
                payload.status,
                payload.expected_status,
            )
            if result is None:
                raise HTTPException(404, "Match saknas eller åtkomst nekas")
            return result
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc

    @app.get("/api/reporter/reporting/events")
    def reporter_event_matches(authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        return admin_event_matches(OWNER_ACCOUNT_ID, int(identity["tid"]))

    @app.get("/api/reporter/reporting/matches/{match_id}/events")
    def reporter_match_events(match_id: int, authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        _require_reporter_match(int(identity["tid"]), match_id)
        return admin_match_events(OWNER_ACCOUNT_ID, int(identity["tid"]), match_id)

    @app.put("/api/reporter/reporting/matches/{match_id}/events/{player_id}")
    def reporter_put_event(match_id: int, player_id: int, payload: ReporterEventWrite, authorization: str | None = Header(default=None)):
        identity = _reporter_identity(authorization)
        _require_reporter_match(int(identity["tid"]), match_id)
        try:
            return update_player_match_events(OWNER_ACCOUNT_ID, int(identity["tid"]), match_id, player_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
