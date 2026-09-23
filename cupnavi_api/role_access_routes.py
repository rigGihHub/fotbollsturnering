"""Tournament-scoped role codes and narrow match-reporter sessions for Next admin."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone

from fastapi import Header, HTTPException, Request
from pydantic import BaseModel

from cupnavi_core.rate_limit import consume_rate_limit
from cupnavi_core.team_portal import generate_short_numeric_code, new_code_hash, verify_access_code
from cupnavi_core.match_status import MATCH_FINISHED, normalize_match_status
from .admin_auth import OWNER_ACCOUNT_ID
from .admin_repository import _has_tournament_access
from .match_events_admin_repository import admin_event_matches, admin_match_events, update_player_match_events
from .publish_reporting_repository import admin_reporting, save_result, set_reporter_match_status
from .repository import connect, one, all_rows, _dict_rows

MAX_REPORTER_SESSION_SECONDS = 60 * 60 * 24 * 3
_REPORTER_SCHEMA_READY = False


class ReporterLogin(BaseModel):
    code: str
    cup: str | None = None  # Older clients may still supply a cup hint.


class ReporterCodeRotate(BaseModel):
    valid_hours: int = 48


class ReporterCodeExtend(BaseModel):
    additional_hours: int = 24


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
    global _REPORTER_SCHEMA_READY
    if _REPORTER_SCHEMA_READY:
        return
    with connect() as con:
        con.execute("BEGIN IMMEDIATE")
        con.execute(
            """CREATE TABLE IF NOT EXISTS match_reporter_credentials (
                tournament_id INTEGER PRIMARY KEY REFERENCES tournaments(id) ON DELETE CASCADE,
                code_salt TEXT NOT NULL,
                code_hash TEXT NOT NULL,
                created_at TEXT NOT NULL,
                rotated_at TEXT,
                valid_hours INTEGER NOT NULL DEFAULT 48,
                expires_at TEXT
            )"""
        )
        columns = {str(row[1]) for row in con.execute("PRAGMA table_info(match_reporter_credentials)").fetchall()}
        if "valid_hours" not in columns:
            con.execute("ALTER TABLE match_reporter_credentials ADD COLUMN valid_hours INTEGER NOT NULL DEFAULT 48")
        if "code_lookup" not in columns:
            con.execute("ALTER TABLE match_reporter_credentials ADD COLUMN code_lookup TEXT")
        if "expires_at" not in columns:
            con.execute("ALTER TABLE match_reporter_credentials ADD COLUMN expires_at TEXT")
        con.execute("CREATE UNIQUE INDEX IF NOT EXISTS reporter_code_lookup_unique ON match_reporter_credentials(code_lookup)")
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    _REPORTER_SCHEMA_READY = True


def _credential(tournament_id: int):
    _ensure_reporter_table()
    return one(
        "SELECT tournament_id,code_salt,code_hash,created_at,rotated_at,valid_hours,code_lookup,expires_at FROM match_reporter_credentials WHERE tournament_id=?",
        (int(tournament_id),),
    )


def _credential_expiry(row) -> int:
    """Absolute UTC deadline; old seven-day codes are also capped at three days."""
    if not row:
        return 0
    try:
        explicit_expiry = row.get("expires_at")
        if explicit_expiry:
            expiry = datetime.fromisoformat(str(explicit_expiry))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return int(expiry.timestamp())
        issued = datetime.fromisoformat(str(row.get("rotated_at") or row.get("created_at") or ""))
        if issued.tzinfo is None:
            issued = issued.replace(tzinfo=timezone.utc)
        duration = min(MAX_REPORTER_SESSION_SECONDS, max(1, int(row.get("valid_hours") or 48)) * 3600)
        return int(issued.timestamp()) + duration
    except (ValueError, TypeError, OverflowError):
        return 0


def _code_lookup(code: str) -> str:
    return hmac.new(_session_secret(), ("reporter-code\0" + code).encode(), hashlib.sha256).hexdigest()


def _find_reporter_credential(code: str):
    _ensure_reporter_table()
    # Legacy salted codes stay usable for their remaining lifetime. They are
    # checked for ambiguity, never assigned to the first matching tournament.
    candidates = all_rows(
        "SELECT c.* FROM match_reporter_credentials c JOIN tournaments t ON t.id=c.tournament_id "
        "WHERE (c.code_lookup=? OR c.code_lookup IS NULL) "
        "AND COALESCE(t.lifecycle_status,'draft') NOT IN ('trashed','purged')",
        (_code_lookup(code),),
    )
    matches = [row for row in candidates if _credential_expiry(row) > time.time()
               and verify_access_code(code, row["code_salt"], row["code_hash"])]
    return matches[0] if len(matches) == 1 else None


def reporter_code_status(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    row = _credential(tournament_id)
    return {
        "active": _credential_expiry(row) > time.time(),
        "created_at": row.get("created_at") if row else None,
        "rotated_at": row.get("rotated_at") if row else None,
        "valid_hours": max(1, min(72, int(row.get("valid_hours") or 48))) if row else 48,
        "expires_at": datetime.fromtimestamp(_credential_expiry(row), timezone.utc).isoformat() if row and _credential_expiry(row) else None,
    }


def rotate_reporter_code(account_id: int, tournament_id: int, valid_hours: int = 48):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    valid_hours = max(1, min(72, int(valid_hours)))
    _ensure_reporter_table()
    with connect() as con:
        # Allocation and rotation share a write transaction across API workers.
        con.execute("BEGIN IMMEDIATE")
        rows = _dict_rows(con.execute("SELECT * FROM match_reporter_credentials"))
        active = [row for row in rows if _credential_expiry(row) > time.time()
                  or int(row["tournament_id"]) == int(tournament_id)]
        for _ in range(128):
            code = generate_short_numeric_code(4)
            lookup = _code_lookup(code)
            if not any(row.get("code_lookup") == lookup or
                       (not row.get("code_lookup") and verify_access_code(code, row["code_salt"], row["code_hash"]))
                       for row in active):
                break
        else:
            raise HTTPException(503, "Ingen ledig rapportörskod just nu. Försök igen senare.")
        salt, digest = new_code_hash(code)
        now = datetime.now(timezone.utc).isoformat(timespec="microseconds")
        # An expired reservation can be reused; active reservations cannot.
        con.execute("UPDATE match_reporter_credentials SET code_lookup=NULL WHERE code_lookup=?", (lookup,))
        con.execute(
            "INSERT INTO match_reporter_credentials(tournament_id,code_salt,code_hash,created_at,rotated_at,valid_hours,code_lookup,expires_at) "
            "VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(tournament_id) DO UPDATE SET "
            "code_salt=excluded.code_salt,code_hash=excluded.code_hash,rotated_at=excluded.rotated_at,"
            "valid_hours=excluded.valid_hours,code_lookup=excluded.code_lookup,expires_at=excluded.expires_at",
            (int(tournament_id), salt, digest, now, now, valid_hours, lookup, (datetime.fromtimestamp(time.time()+valid_hours*3600, timezone.utc).isoformat())),
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


def _issue_reporter_session(tournament_id: int, revision: str, valid_hours: int = 48, *, expires_at: int | None = None) -> str:
    now = int(time.time())
    expiry = now + min(MAX_REPORTER_SESSION_SECONDS, max(1, int(valid_hours)) * 60 * 60)
    if expires_at is not None:
        expiry = min(expiry, expires_at)
    payload = {"tid": int(tournament_id), "role": "reporter", "rev": revision, "iat": now, "exp": expiry}
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
        if _credential_expiry(row) <= time.time() or not _find_cup(str(payload["tid"])):
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
    row = one("SELECT * FROM matches WHERE id=? AND tournament_id=?", (int(match_id), int(tournament_id)))
    if not row:
        raise HTTPException(404, "Match saknas eller tillhör en annan cup")
    return row

def _require_reporter_editable_match(tournament_id: int, match_id: int):
    row = _require_reporter_match(tournament_id, match_id)
    if normalize_match_status(row.get("match_status"), has_result=False) == MATCH_FINISHED:
        raise HTTPException(409, "Matchen är slutmarkerad. Endast administratören kan korrigera den.")
    return row


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

    @app.post("/api/admin/cups/{tournament_id}/role-codes/reporter/extend")
    def post_extend_reporter_code(tournament_id: int, payload: ReporterCodeExtend, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        if not _has_tournament_access(int(account["id"]), tournament_id):
            raise HTTPException(404, "Cup not found or access denied")
        additional_hours = max(1, min(72, int(payload.additional_hours)))
        row = _credential(tournament_id)
        if not row:
            raise HTTPException(404, "Ingen rapportörskod finns")
        current = _credential_expiry(row)
        base = max(int(time.time()), current)
        expires = datetime.fromtimestamp(base + additional_hours * 3600, timezone.utc).isoformat()
        with connect() as con:
            con.execute("UPDATE match_reporter_credentials SET expires_at=? WHERE tournament_id=?", (expires, int(tournament_id)))
            commit = getattr(con, "commit", None)
            if callable(commit): commit()
        return reporter_code_status(int(account["id"]), tournament_id)

    @app.delete("/api/admin/cups/{tournament_id}/role-codes/reporter")
    def delete_reporter_code(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        if not _has_tournament_access(int(account["id"]), tournament_id):
            raise HTTPException(404, "Cup not found or access denied")
        _ensure_reporter_table()
        with connect() as con:
            con.execute("DELETE FROM match_reporter_credentials WHERE tournament_id=?", (int(tournament_id),))
            commit = getattr(con, "commit", None)
            if callable(commit): commit()
        return {"deleted": True, **reporter_code_status(int(account["id"]), tournament_id)}

    @app.post("/api/reporter/session")
    def reporter_login(payload: ReporterLogin, request: Request):
        # Neither changing the code nor supplying a different cup bypasses this limit.
        subject = hashlib.sha256(f"{request.client.host if request.client else ''}".encode()).hexdigest()
        with connect() as con:
            allowed, retry_after, _ = consume_rate_limit(con, scope="reporter_login", subject_hash=subject, limit=10, window_seconds=900)
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        if not allowed:
            raise HTTPException(429, "För många kodförsök", headers={"Retry-After": str(retry_after)})
        if not re.fullmatch(r"[0-9]{4}", payload.code):
            raise HTTPException(401, "Felaktig eller utgången kod. Be arrangören om en aktuell kod.")
        credential = _find_reporter_credential(payload.code)
        cup = _find_cup(str(credential["tournament_id"])) if credential else None
        hinted_cup = _find_cup(payload.cup) if payload.cup else cup
        if not credential or not cup or not hinted_cup or hinted_cup["id"] != cup["id"]:
            raise HTTPException(401, "Felaktig eller utgången kod. Be arrangören om en aktuell kod.")
        revision = str(credential.get("rotated_at") or credential.get("created_at") or "")
        return {"token": _issue_reporter_session(int(cup["id"]), revision, int(credential.get("valid_hours") or 48), expires_at=_credential_expiry(credential)), "cup": cup, "role": "reporter"}

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
        _require_reporter_editable_match(int(identity["tid"]), match_id)
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
        _require_reporter_editable_match(int(identity["tid"]), match_id)
        try:
            return update_player_match_events(OWNER_ACCOUNT_ID, int(identity["tid"]), match_id, player_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(409, str(exc)) from exc
