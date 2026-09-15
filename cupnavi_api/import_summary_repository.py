"""Summarize what a saved document import found and what is now persisted."""
from __future__ import annotations

import json
from datetime import date

from .admin_repository import _has_tournament_access
from .initial_import_idempotency import apply_document_matches_idempotent
from .repository import connect, one


def _count(sql: str, tournament_id: int) -> int:
    row = one(sql, (int(tournament_id),)) or {}
    return int(row.get("n") or 0)


def import_summary(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    snapshot = one(
        """SELECT payload_json,source_name FROM tournament_setup_imports
           WHERE tournament_id=? AND import_kind='initial_setup'
           ORDER BY id DESC LIMIT 1""",
        (int(tournament_id),),
    )
    if not snapshot:
        return {"available": False}
    try:
        payload = json.loads(str(snapshot.get("payload_json") or "{}"))
    except (TypeError, json.JSONDecodeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}

    teams = [row for row in (payload.get("teams") or []) if isinstance(row, dict)]
    groups = {
        str(row.get("group_name") or "").strip().casefold()
        for row in teams
        if str(row.get("group_name") or "").strip()
    }
    expected = {
        "teams": len(teams),
        "groups": len(groups),
        "matches": len(payload.get("matches") or []),
        "pitches": len(payload.get("venues") or []),
        "pitch_windows": len(payload.get("pitch_windows") or []),
        "playoff_matches": len(payload.get("playoff_matches") or []),
        "rules": len(payload.get("rules") or []),
    }
    actual = {
        "teams": _count("SELECT COUNT(*) AS n FROM teams WHERE tournament_id=?", tournament_id),
        "groups": _count("SELECT COUNT(*) AS n FROM groups WHERE tournament_id=?", tournament_id),
        "matches": _count("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NULL", tournament_id),
        "pitches": _count("SELECT COUNT(*) AS n FROM pitches WHERE tournament_id=?", tournament_id),
        "pitch_windows": _count("SELECT COUNT(*) AS n FROM pitch_day_windows WHERE tournament_id=? AND confirmed=1", tournament_id),
        "playoff_matches": _count("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=? AND bracket_id IS NOT NULL", tournament_id),
    }
    pending = []
    if expected["pitch_windows"] and actual["pitch_windows"] < expected["pitch_windows"]:
        pending.append("pitch_windows")
    if expected["playoff_matches"] and actual["playoff_matches"] < expected["playoff_matches"]:
        pending.append("playoff_matches")

    return {
        "available": True,
        "source_name": snapshot.get("source_name") or payload.get("source_name"),
        "expected": expected,
        "actual": actual,
        "pending": pending,
        "complete": not pending,
        "warnings": payload.get("warnings") or [],
    }


def restore_initial_matches(account_id: int, tournament_id: int):
    """Restore reviewed first-import matches without asking for the files again."""
    if not _has_tournament_access(account_id, tournament_id):
        return None
    if _count("SELECT COUNT(*) AS n FROM matches WHERE tournament_id=?", tournament_id):
        raise ValueError("Schemat innehåller redan matcher och kan inte återställas ovanpå dem")
    snapshot = one(
        """SELECT payload_json FROM tournament_setup_imports
           WHERE tournament_id=? AND import_kind='initial_setup'
           ORDER BY id DESC LIMIT 1""",
        (int(tournament_id),),
    )
    if not snapshot:
        raise ValueError("Ingen tidigare cupimport finns sparad")
    try:
        payload = json.loads(str(snapshot.get("payload_json") or "{}"))
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Den sparade cupimporten kunde inte läsas") from exc
    matches = payload.get("matches") if isinstance(payload, dict) else None
    if not isinstance(matches, list) or not matches:
        raise ValueError("Den första cupimporten innehöll inga matcher")
    tournament = one("SELECT start_date FROM tournaments WHERE id=?", (int(tournament_id),)) or {}
    try:
        fallback_date = date.fromisoformat(str(tournament.get("start_date") or ""))
    except ValueError as exc:
        raise ValueError("Ange cupens startdatum innan matcherna återställs") from exc
    created, replay = apply_document_matches_idempotent(connect, tournament_id, payload, fallback_date)
    return {"restored": True, "restored_count": created, "idempotent_replay": replay}
