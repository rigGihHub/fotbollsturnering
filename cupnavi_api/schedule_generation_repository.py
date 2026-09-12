"""Organizer-scoped autoschedule preview/apply using CupNavi's existing scheduler repository."""
from __future__ import annotations

from cupnavi_core.schedule_generation import build_schedule_preview
from cupnavi_core.schedule_repository import ScheduleRepository

from .admin_repository import _has_tournament_access
from .repository import all_rows, connect, one


def _inputs(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))
    if not tournament:
        return None
    rules = one("SELECT * FROM schedule_rules WHERE tournament_id=?", (int(tournament_id),)) or {}
    # schedule_domain historically reads extra_time_minutes. The current persisted
    # setting is playoff_extra_time_minutes, so expose the legacy domain alias here.
    if "extra_time_minutes" not in tournament:
        tournament["extra_time_minutes"] = tournament.get("playoff_extra_time_minutes") or 0
    referees = all_rows("SELECT id FROM referees WHERE tournament_id=? ORDER BY id", (int(tournament_id),))
    matches = all_rows(
        """SELECT * FROM matches WHERE tournament_id=?
           ORDER BY CASE stage WHEN 'Gruppspel' THEN 1 WHEN 'Kvartsfinal' THEN 2
                    WHEN 'Semifinal' THEN 3 WHEN 'Bronsmatch' THEN 4 WHEN 'Final' THEN 5 ELSE 6 END,
                    group_id,bracket_id,round_no,match_no,id""",
        (int(tournament_id),),
    )
    return tournament, rules, referees, matches


def preview_generated_schedule(account_id: int, tournament_id: int):
    inputs = _inputs(account_id, tournament_id)
    if inputs is None:
        return None
    tournament, rules, referees, matches = inputs
    if not matches:
        raise ValueError("Det finns inga matcher att schemalägga ännu. Skapa gruppmatcher först.")
    required = ("first_match_time", "latest_kickoff_time", "halves", "minutes_per_half", "halftime_minutes")
    missing = [field for field in required if rules.get(field) in (None, "")]
    if missing:
        raise ValueError("Schemainställningarna är ofullständiga: " + ", ".join(missing))
    preview = build_schedule_preview(matches, tournament, rules, referees=referees)
    preview["tournament_id"] = int(tournament_id)
    return preview


def apply_generated_schedule(account_id: int, tournament_id: int, *, allow_partial: bool = False):
    """Recompute immediately before persist so a stale browser preview cannot be applied."""
    preview = preview_generated_schedule(account_id, tournament_id)
    if preview is None:
        return None
    if not preview["updates"]:
        raise ValueError("Autoschemat innehåller inga nya schemaläggningar att spara.")
    if preview["unresolved_count"] and not allow_partial:
        raise ValueError(
            f"{preview['unresolved_count']} matcher kan inte schemaläggas säkert ännu. "
            "Inget har sparats. Lös beroendena eller välj uttryckligen delvis schema."
        )
    updates = [
        (row["scheduled_start"], row["pitch_number"], row.get("referee_id"), row["id"])
        for row in preview["updates"]
    ]
    repository = ScheduleRepository(all_rows, connect)
    repository.persist_generated_schedule(
        int(tournament_id),
        updates,
        int(preview["unresolved_count"]),
        preserve_existing=True,
    )
    return {
        **preview,
        "applied": True,
        "applied_count": len(updates),
        "partial": bool(preview["unresolved_count"]),
    }
