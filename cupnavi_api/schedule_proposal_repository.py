"""Organizer-scoped adapter for deterministic schedule proposals."""
from __future__ import annotations

from .admin_repository import _has_tournament_access
from .repository import _dict_rows, connect
from .schedule_admin_repository import admin_schedule
from .schedule_conflicts import analyze_schedule_conflicts
from .schedule_proposal import build_schedule_proposal
from .venue_admin_repository import admin_venues


class ProposalStaleError(ValueError):
    """Raised when proposal inputs changed after the organizer reviewed them."""


def _first(cursor):
    rows = _dict_rows(cursor)
    return rows[0] if rows else None


def _load_source(con, tournament_id: int):
    tournament_id = int(tournament_id)
    rules = _first(
        con.execute(
            """SELECT pitch_count,halves,minutes_per_half,halftime_minutes,pitch_break_minutes,
                      minimum_team_rest_minutes
               FROM schedule_rules WHERE tournament_id=?""",
            (tournament_id,),
        )
    ) or {
        "pitch_count": 1,
        "halves": 2,
        "minutes_per_half": 20,
        "halftime_minutes": 5,
        "pitch_break_minutes": 0,
        "minimum_team_rest_minutes": 0,
    }
    pitch_count = max(1, int(rules.get("pitch_count") or 1))
    # SELECT * is deliberate here: legacy SQLite fixtures predate bracket_id,
    # while current production rows include it. The proposal engine only reads
    # known keys and therefore stays compatible with both schemas.
    matches = _dict_rows(
        con.execute(
            "SELECT * FROM matches WHERE tournament_id=? ORDER BY id",
            (tournament_id,),
        )
    )
    for row in matches:
        row["schedule_locked"] = bool(row.get("schedule_locked") or 0)
        row["played"] = row.get("home_score") is not None and row.get("away_score") is not None
    windows = _dict_rows(
        con.execute(
            """SELECT pitch_number,play_date,start_time,end_time,confirmed
               FROM pitch_day_windows
               WHERE tournament_id=? AND pitch_number<=?
               ORDER BY play_date,pitch_number""",
            (tournament_id, pitch_count),
        )
    )
    return matches, rules, windows


def _proposal_source(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    if admin_venues(account_id, tournament_id) is None:
        return None
    with connect() as con:
        return _load_source(con, tournament_id)


def admin_schedule_proposal(account_id: int, tournament_id: int):
    source = _proposal_source(account_id, tournament_id)
    if source is None:
        return None
    matches, rules, windows = source
    proposal = build_schedule_proposal(matches, rules, windows)
    schedule = admin_schedule(account_id, tournament_id)
    return {
        **proposal,
        "source_match_count": len(matches),
        "window_count": len(windows),
        "existing_conflict_analysis": schedule["conflict_analysis"] if schedule else None,
    }


def apply_schedule_proposal(account_id: int, tournament_id: int, fingerprint: str):
    """Atomically apply the server-rebuilt proposal only if its source is unchanged."""
    if not _has_tournament_access(account_id, tournament_id):
        return None
    if not fingerprint or len(str(fingerprint)) != 64:
        raise ValueError("Schemaförslagets fingerprint saknas eller är ogiltigt")
    if admin_venues(account_id, tournament_id) is None:
        return None

    tournament_id = int(tournament_id)
    con = None
    try:
        with connect() as con:
            con.execute("BEGIN IMMEDIATE")
            matches, rules, windows = _load_source(con, tournament_id)
            proposal = build_schedule_proposal(matches, rules, windows)
            if proposal["fingerprint"] != str(fingerprint):
                con.rollback()
                raise ProposalStaleError(
                    "Schemaförslaget är inaktuellt eftersom matcher, regler eller planfönster har ändrats. Räkna om förslaget."
                )

            by_id = {int(row["id"]): dict(row) for row in matches}
            for placement in proposal["placements"]:
                row = by_id[int(placement["match_id"])]
                row["scheduled_start"] = placement["scheduled_start"]
                row["pitch_number"] = int(placement["pitch_number"])
            final_analysis = analyze_schedule_conflicts(list(by_id.values()), rules)
            if int(final_analysis.get("error_count") or 0) > 0:
                con.rollback()
                raise ValueError(
                    "Förslaget gav en blockerande schemakrock vid slutkontrollen och har inte sparats"
                )

            applied = 0
            for placement in proposal["placements"]:
                cursor = con.execute(
                    """UPDATE matches
                       SET scheduled_start=?,pitch_number=?,schedule_published=0
                       WHERE id=? AND tournament_id=?
                         AND scheduled_start IS NULL AND pitch_number IS NULL
                         AND COALESCE(schedule_locked,0)=0
                         AND home_score IS NULL AND away_score IS NULL""",
                    (
                        placement["scheduled_start"],
                        int(placement["pitch_number"]),
                        int(placement["match_id"]),
                        tournament_id,
                    ),
                )
                if getattr(cursor, "rowcount", 1) != 1:
                    con.rollback()
                    raise ProposalStaleError(
                        "En match ändrades medan schemaförslaget applicerades. Ingenting sparades; räkna om förslaget."
                    )
                applied += 1
            if applied:
                con.execute(
                    "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
                    (tournament_id,),
                )
            con.commit()
    except (ProposalStaleError, ValueError):
        raise

    schedule = admin_schedule(account_id, tournament_id)
    return {
        "applied": True,
        "applied_count": applied,
        "fingerprint": str(fingerprint),
        "unresolved_count": int(proposal.get("unresolved_count") or 0),
        "post_apply_conflict_analysis": schedule["conflict_analysis"] if schedule else final_analysis,
        "schedule": schedule,
    }
