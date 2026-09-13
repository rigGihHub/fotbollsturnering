"""Review-safe bulk schedule revision support for document/photo updates."""
from __future__ import annotations

from datetime import datetime

from .schedule_admin_repository import admin_schedule
from .schedule_conflicts import analyze_schedule_conflicts
from .repository import connect, one


def _parse_start(value, *, start_date, end_date, row_no: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"Rad {row_no}: matchtid saknas")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"Rad {row_no}: matchtiden måste innehålla datum och klockslag") from exc
    iso_date = parsed.date().isoformat()
    if start_date and iso_date < str(start_date):
        raise ValueError(f"Rad {row_no}: matchtiden ligger före cupens första dag")
    if end_date and iso_date > str(end_date):
        raise ValueError(f"Rad {row_no}: matchtiden ligger efter cupens sista dag")
    return parsed.isoformat(timespec="minutes")


def apply_schedule_revision(account_id: int, tournament_id: int, changes: list[dict]):
    """Apply a reviewed set of changed schedule placements atomically.

    Every row carries the schedule values seen during review. If any of those values
    changed before commit, the whole revision is rejected instead of partially
    overwriting a newer edit.
    """
    payload = admin_schedule(account_id, tournament_id)
    if payload is None:
        return None
    rows = [dict(item) for item in (changes or []) if isinstance(item, dict)]
    if not rows:
        raise ValueError("Det finns inga granskade schemaändringar att importera")
    if len(rows) > 500:
        raise ValueError("Högst 500 schemaändringar kan importeras åt gången")

    current_by_id = {int(row["id"]): dict(row) for row in payload["matches"]}
    seen: set[int] = set()
    clean: list[dict] = []
    start_date = payload.get("start_date")
    end_date = payload.get("end_date") or start_date
    pitch_count = int(payload.get("pitch_count") or 1)

    for row_no, row in enumerate(rows, start=1):
        try:
            match_id = int(row.get("match_id"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Rad {row_no}: ogiltigt match-id") from exc
        if match_id in seen:
            raise ValueError(f"Rad {row_no}: samma match förekommer flera gånger")
        seen.add(match_id)
        current = current_by_id.get(match_id)
        if not current:
            raise ValueError(f"Rad {row_no}: matchen finns inte längre i cupen")
        if bool(current.get("played")):
            raise ValueError(f"Rad {row_no}: en färdigspelad match kan inte ändras")
        if bool(current.get("schedule_locked")):
            raise ValueError(f"Rad {row_no}: matchen är låst och måste låsas upp först")

        expected_start = row.get("expected_scheduled_start") or None
        current_start = current.get("scheduled_start") or None
        expected_pitch = row.get("expected_pitch_number")
        expected_pitch = int(expected_pitch) if expected_pitch not in (None, "") else None
        current_pitch = current.get("pitch_number")
        current_pitch = int(current_pitch) if current_pitch not in (None, "") else None
        if expected_start != current_start or expected_pitch != current_pitch:
            raise ValueError(
                f"Rad {row_no}: schemat har ändrats sedan granskningen. Läs in revisionen igen innan du sparar."
            )

        scheduled_start = _parse_start(
            row.get("scheduled_start"), start_date=start_date, end_date=end_date, row_no=row_no
        )
        try:
            pitch_number = int(row.get("pitch_number"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Rad {row_no}: plan saknas eller är ogiltig") from exc
        if pitch_number < 1 or pitch_number > pitch_count:
            raise ValueError(f"Rad {row_no}: plan måste vara mellan 1 och {pitch_count}")
        clean.append({
            "match_id": match_id,
            "scheduled_start": scheduled_start,
            "pitch_number": pitch_number,
        })

    # Reject a revision that introduces additional hard schedule conflicts.
    rules = one(
        """SELECT pitch_count,first_match_time,latest_kickoff_time,
                  halves,minutes_per_half,halftime_minutes,pitch_break_minutes,
                  minimum_team_rest_minutes
           FROM schedule_rules WHERE tournament_id=?""",
        (int(tournament_id),),
    ) or {}
    baseline = payload.get("conflict_analysis") or analyze_schedule_conflicts(payload["matches"], rules)
    candidate = [dict(row) for row in payload["matches"]]
    patch_by_id = {row["match_id"]: row for row in clean}
    for match in candidate:
        patch = patch_by_id.get(int(match["id"]))
        if patch:
            match["scheduled_start"] = patch["scheduled_start"]
            match["pitch_number"] = patch["pitch_number"]
    candidate_analysis = analyze_schedule_conflicts(candidate, rules)
    if int(candidate_analysis.get("error_count") or 0) > int(baseline.get("error_count") or 0):
        first = next((item for item in candidate_analysis.get("conflicts", []) if item.get("severity") == "error"), None)
        message = (first or {}).get("message") or "Revisionen skapar en ny schemakrock"
        raise ValueError(f"Revisionen stoppades av schemakontrollen: {message}")

    with connect() as con:
        try:
            for row in clean:
                con.execute(
                    """UPDATE matches
                       SET scheduled_start=?,pitch_number=?,schedule_published=0
                       WHERE id=? AND tournament_id=?""",
                    (row["scheduled_start"], row["pitch_number"], row["match_id"], int(tournament_id)),
                )
            con.execute(
                "UPDATE tournaments SET schedule_dirty=1,is_published=0 WHERE id=?",
                (int(tournament_id),),
            )
            commit = getattr(con, "commit", None)
            if callable(commit):
                commit()
        except Exception:
            rollback = getattr(con, "rollback", None)
            if callable(rollback):
                rollback()
            raise

    result = admin_schedule(account_id, tournament_id)
    return {
        "applied": True,
        "applied_count": len(clean),
        "schedule": result,
        "conflict_analysis": (result or {}).get("conflict_analysis"),
    }
