"""Database-backed participant resolution for CupNavi API read models."""
from __future__ import annotations

from cupnavi_core.participant_resolution import ParticipantResolver, finalized_group_standings

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


def participant_resolution_payload(tournament: dict, matches: list[dict]) -> dict[str, dict]:
    """Return additive resolved participant data keyed by public match id.

    Existing public ``matches`` and ``brackets`` are contractual parity surfaces
    and therefore remain byte-for-byte repository shaped. Consumers that want
    actual team identities for symbolic sources use this sidecar read model.
    """
    if not tournament or not matches:
        return {}
    resolver = tournament_participant_resolver(tournament)
    result: dict[str, dict] = {}
    for match in matches:
        match_id = match.get("id")
        if match_id is None:
            continue
        home = resolver.resolve(match.get("home_source"))
        away = resolver.resolve(match.get("away_source"))
        result[str(int(match_id))] = {
            "home": home.as_dict(),
            "away": away.as_dict(),
        }
    return result


def resolve_public_snapshot(snapshot: dict) -> dict:
    """Add a sidecar participant-resolution map without changing public rows."""
    if not snapshot or not snapshot.get("tournament"):
        return snapshot
    result = dict(snapshot)
    public_matches = list(snapshot.get("matches") or [])
    result["participant_resolution"] = participant_resolution_payload(
        snapshot["tournament"], public_matches
    )
    return result


def public_bracket_resolution(tournament: dict, brackets: list[dict]) -> dict[str, dict]:
    public_matches = [
        match
        for bracket in brackets
        for match in (bracket.get("matches") or [])
    ]
    return participant_resolution_payload(tournament, public_matches)
