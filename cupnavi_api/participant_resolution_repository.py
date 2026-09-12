"""Database-backed participant resolution for CupNavi API read models."""
from __future__ import annotations

from cupnavi_core.participant_resolution import (
    ParticipantResolver,
    enrich_match_participants,
    finalized_group_standings,
)

from .repository import all_rows


def tournament_participant_resolver(tournament: dict) -> ParticipantResolver:
    tournament_id = int(tournament["id"])
    teams = all_rows(
        "SELECT id,name,group_id FROM teams WHERE tournament_id=? ORDER BY name,id",
        (tournament_id,),
    )
    matches = all_rows(
        """SELECT id,group_id,bracket_id,stage,round_no,match_no,home_source,away_source,
                  scheduled_start,pitch_number,home_score,away_score,home_penalties,away_penalties,
                  decided_winner_id,schedule_published
           FROM matches WHERE tournament_id=? ORDER BY id""",
        (tournament_id,),
    )
    standings = finalized_group_standings(
        teams,
        matches,
        points_win=int(tournament.get("points_win") or 0),
        points_draw=int(tournament.get("points_draw") or 0),
        points_loss=int(tournament.get("points_loss") or 0),
        table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
    )
    return ParticipantResolver(teams=teams, matches=matches, standings_by_group=standings)


def resolve_public_snapshot(snapshot: dict) -> dict:
    """Add resolved participant names to a public snapshot without exposing hidden rows."""
    if not snapshot or not snapshot.get("tournament"):
        return snapshot
    resolver = tournament_participant_resolver(snapshot["tournament"])
    result = dict(snapshot)
    result["matches"] = enrich_match_participants(list(snapshot.get("matches") or []), resolver)
    brackets = []
    for bracket in snapshot.get("brackets") or []:
        item = dict(bracket)
        item["matches"] = enrich_match_participants(list(bracket.get("matches") or []), resolver)
        brackets.append(item)
    result["brackets"] = brackets
    return result


def resolve_public_brackets(tournament: dict, brackets: list[dict]) -> list[dict]:
    resolver = tournament_participant_resolver(tournament)
    result = []
    for bracket in brackets:
        item = dict(bracket)
        item["matches"] = enrich_match_participants(list(bracket.get("matches") or []), resolver)
        result.append(item)
    return result
