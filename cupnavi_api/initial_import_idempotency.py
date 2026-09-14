"""Idempotency guard for the reviewed initial match import.

The legacy importer is intentionally conservative and refuses to write when a
cup already has matches. That protects existing schedules, but it also turns a
perfectly identical retry (for example after a lost HTTP response) into an
error. This module keeps the conservative behaviour for different schedules
while treating an exact replay as a successful no-op.
"""
from __future__ import annotations

from datetime import datetime

from cupnavi_core.cup_document_creator_view import apply_document_matches as _apply_document_matches, managed_connection


def _name(value) -> str:
    return " ".join(str(value or "").split()).casefold()


def _start(value) -> str:
    if isinstance(value, datetime):
        return value.isoformat(timespec="minutes")
    raw = str(value or "").strip().replace(" ", "T")
    if not raw:
        return ""
    try:
        return datetime.fromisoformat(raw).isoformat(timespec="minutes")
    except ValueError:
        return raw[:16]


def _imported_start(value, fallback_date) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("En importerad match saknar tid.")
    for fmt in ("%H:%M", "%H.%M"):
        try:
            tm = datetime.strptime(raw, fmt).time()
            return datetime.combine(fallback_date, tm).isoformat(timespec="minutes")
        except ValueError:
            pass
    try:
        return datetime.fromisoformat(raw.replace("T", " ")).isoformat(timespec="minutes")
    except ValueError as exc:
        raise ValueError(f"Ogiltig matchtid: {raw}") from exc


def _schedule_matches_proposal(connection_factory, tournament_id: int, prefill: dict, fallback_date) -> bool:
    """Return True only when every existing match exactly matches this import."""
    proposed = list((prefill or {}).get("matches") or [])
    if not proposed:
        return False

    with managed_connection(connection_factory) as con:
        existing = con.execute(
            """SELECT m.group_id,m.stage,m.match_no,m.home_source,m.away_source,
                      m.scheduled_start,p.name AS pitch_name
               FROM matches m
               LEFT JOIN pitches p
                 ON p.tournament_id=m.tournament_id AND p.pitch_number=m.pitch_number
               WHERE m.tournament_id=?
               ORDER BY m.match_no,m.id""",
            (tournament_id,),
        ).fetchall()
        if not existing or len(existing) != len(proposed):
            return False

        teams = con.execute(
            "SELECT id,name,group_id FROM teams WHERE tournament_id=?",
            (tournament_id,),
        ).fetchall()
        team_map = {_name(row[1]): (int(row[0]), row[2]) for row in teams}
        groups = con.execute(
            "SELECT id,name FROM groups WHERE tournament_id=?",
            (tournament_id,),
        ).fetchall()
        group_map = {_name(row[1]): int(row[0]) for row in groups}

        expected = []
        for no, row in enumerate(proposed, start=1):
            home = team_map.get(_name(row.get("home_team")))
            away = team_map.get(_name(row.get("away_team")))
            if not home or not away:
                return False
            group_name = _name(row.get("group_name"))
            group_id = group_map.get(group_name) if group_name else home[1]
            if not group_id or home[1] != group_id or away[1] != group_id:
                return False
            venue = _name(row.get("venue"))
            if not venue:
                return False
            expected.append(
                (
                    int(group_id),
                    "gruppspel",
                    no,
                    f"team:{home[0]}",
                    f"team:{away[0]}",
                    _imported_start(row.get("time"), fallback_date),
                    venue,
                )
            )

        actual = []
        for row in existing:
            actual.append(
                (
                    int(row[0]) if row[0] is not None else None,
                    _name(row[1]),
                    int(row[2]) if row[2] is not None else None,
                    str(row[3] or ""),
                    str(row[4] or ""),
                    _start(row[5]),
                    _name(row[6]),
                )
            )
        return actual == expected


def apply_document_matches_idempotent(connection_factory, tournament_id: int, prefill: dict, fallback_date) -> tuple[int, bool]:
    """Create matches once; an exact retry is a successful no-op.

    Returns ``(created_count, idempotent_replay)``. Any pre-existing schedule
    that is not byte-for-byte equivalent in match identity, time and venue is
    still rejected by the original conservative importer.
    """
    if _schedule_matches_proposal(connection_factory, tournament_id, prefill, fallback_date):
        return 0, True
    try:
        return _apply_document_matches(connection_factory, tournament_id, prefill, fallback_date), False
    except ValueError:
        # A concurrent/ambiguous retry may have committed between our first
        # comparison and the legacy importer's own "existing schedule" guard.
        # Re-check once. Different schedules must still fail closed.
        if _schedule_matches_proposal(connection_factory, tournament_id, prefill, fallback_date):
            return 0, True
        raise
