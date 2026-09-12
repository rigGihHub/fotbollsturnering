"""Organizer-scoped adapter for deterministic schedule proposals."""
from __future__ import annotations

from .repository import one
from .schedule_admin_repository import admin_schedule
from .schedule_proposal import build_schedule_proposal
from .venue_admin_repository import admin_venues


def admin_schedule_proposal(account_id: int, tournament_id: int):
    schedule = admin_schedule(account_id, tournament_id)
    if schedule is None:
        return None
    venues = admin_venues(account_id, tournament_id)
    if venues is None:
        return None
    rules = one(
        """SELECT halves,minutes_per_half,halftime_minutes,pitch_break_minutes,
                  minimum_team_rest_minutes
           FROM schedule_rules WHERE tournament_id=?""",
        (int(tournament_id),),
    ) or {}
    proposal = build_schedule_proposal(schedule["matches"], rules, venues["windows"])
    return {
        **proposal,
        "source_match_count": schedule["match_count"],
        "window_count": len(venues["windows"]),
        "existing_conflict_analysis": schedule["conflict_analysis"],
    }
