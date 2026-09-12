"""Resolve canonical CupNavi participant sources without mutating provenance.

Persisted ``home_source`` / ``away_source`` stay symbolic. This module only
produces a read model (team id/name + resolved state) for UI/API consumers.
"""
from __future__ import annotations

from dataclasses import dataclass

from .participant_sources import parse_participant_source
from .playoff_dependency_safety import winner_side
from .public_competition import calculate_group_table


@dataclass(frozen=True)
class ResolvedParticipant:
    source: str
    team_id: int | None = None
    team_name: str | None = None
    resolved: bool = False
    kind: str = "empty"
    reason: str = ""

    def as_dict(self) -> dict:
        return {
            "source": self.source,
            "kind": self.kind,
            "resolved": self.resolved,
            "team_id": self.team_id,
            "team_name": self.team_name,
            "reason": self.reason,
        }


def finalized_group_standings(
    teams: list[dict],
    matches: list[dict],
    *,
    points_win: int = 3,
    points_draw: int = 1,
    points_loss: int = 0,
    table_tiebreak: str = "Målskillnad först",
) -> dict[int, list[dict]]:
    """Return standings only for groups whose persisted group schedule is complete.

    A partial table must never become a playoff participant. A group therefore
    resolves only when at least one group-stage match exists and every such match
    has both scores registered.
    """
    teams_by_group: dict[int, list[dict]] = {}
    for team in teams:
        group_id = team.get("group_id")
        if group_id is None:
            continue
        teams_by_group.setdefault(int(group_id), []).append(team)

    matches_by_group: dict[int, list[dict]] = {}
    for match in matches:
        if str(match.get("stage") or "") != "Gruppspel" or match.get("group_id") is None:
            continue
        matches_by_group.setdefault(int(match["group_id"]), []).append(match)

    result: dict[int, list[dict]] = {}
    for group_id, group_matches in matches_by_group.items():
        if not group_matches:
            continue
        if any(match.get("home_score") is None or match.get("away_score") is None for match in group_matches):
            continue
        group_teams = teams_by_group.get(group_id, [])
        if not group_teams:
            continue
        result[group_id] = calculate_group_table(
            group_teams,
            group_matches,
            points_win=int(points_win),
            points_draw=int(points_draw),
            points_loss=int(points_loss),
            table_tiebreak=str(table_tiebreak or "Målskillnad först"),
        )
    return result


class ParticipantResolver:
    """Resolve direct, group-qualified and winner/loser participant sources."""

    def __init__(
        self,
        *,
        teams: list[dict],
        matches: list[dict],
        standings_by_group: dict[int, list[dict]] | None = None,
    ):
        self.teams_by_id = {int(team["id"]): team for team in teams if team.get("id") is not None}
        self.matches_by_id = {int(match["id"]): match for match in matches if match.get("id") is not None}
        self.standings_by_group = standings_by_group or {}
        self._cache: dict[str, ResolvedParticipant] = {}

    def _team(self, team_id: int, source: str, kind: str) -> ResolvedParticipant:
        team = self.teams_by_id.get(int(team_id))
        if not team:
            return ResolvedParticipant(source=source, kind=kind, reason="team_missing")
        return ResolvedParticipant(
            source=source,
            team_id=int(team_id),
            team_name=str(team.get("name") or f"Lag {team_id}"),
            resolved=True,
            kind=kind,
        )

    def resolve(self, value, *, _seen_matches: frozenset[int] = frozenset()) -> ResolvedParticipant:
        parsed = parse_participant_source(value)
        cache_key = parsed.raw
        if not _seen_matches and cache_key in self._cache:
            return self._cache[cache_key]

        if parsed.kind == "team":
            result = self._team(int(parsed.source_id), parsed.raw, parsed.kind)
        elif parsed.kind == "group":
            rows = self.standings_by_group.get(int(parsed.source_id), [])
            placement = int(parsed.placement or 0)
            row = next((item for item in rows if int(item.get("position") or 0) == placement), None)
            if row is None:
                result = ResolvedParticipant(parsed.raw, kind=parsed.kind, reason="group_not_final")
            else:
                result = self._team(int(row["team_id"]), parsed.raw, parsed.kind)
        elif parsed.kind in {"winner", "loser"}:
            match_id = int(parsed.source_id)
            if match_id in _seen_matches:
                result = ResolvedParticipant(parsed.raw, kind=parsed.kind, reason="dependency_cycle")
            else:
                result = self._resolve_match_outcome(match_id, parsed.kind, _seen_matches | {match_id}, parsed.raw)
        elif parsed.kind == "legacy":
            result = ResolvedParticipant(parsed.raw, team_name=parsed.raw or None, kind=parsed.kind, reason="legacy_source")
        else:
            result = ResolvedParticipant(parsed.raw, kind=parsed.kind, reason=f"{parsed.kind}_source")

        if not _seen_matches:
            self._cache[cache_key] = result
        return result

    def _resolve_match_outcome(
        self,
        match_id: int,
        outcome: str,
        seen_matches: frozenset[int],
        source: str,
    ) -> ResolvedParticipant:
        match = self.matches_by_id.get(int(match_id))
        if not match:
            return ResolvedParticipant(source, kind=outcome, reason="source_match_missing")

        home = self.resolve(match.get("home_source"), _seen_matches=seen_matches)
        away = self.resolve(match.get("away_source"), _seen_matches=seen_matches)
        if not home.resolved or not away.resolved:
            return ResolvedParticipant(source, kind=outcome, reason="source_participant_unresolved")

        decided_winner_id = match.get("decided_winner_id")
        winner_id = None
        if decided_winner_id is not None:
            try:
                winner_id = int(decided_winner_id)
            except (TypeError, ValueError):
                winner_id = None

        if winner_id not in {home.team_id, away.team_id}:
            side = winner_side(
                home_score=match.get("home_score"),
                away_score=match.get("away_score"),
                home_penalties=match.get("home_penalties"),
                away_penalties=match.get("away_penalties"),
            )
            if side == "home":
                winner_id = home.team_id
            elif side == "away":
                winner_id = away.team_id
            else:
                return ResolvedParticipant(source, kind=outcome, reason="source_match_not_decided")

        team_id = winner_id if outcome == "winner" else (away.team_id if winner_id == home.team_id else home.team_id)
        return self._team(int(team_id), source, outcome)


def enrich_match_participants(matches: list[dict], resolver: ParticipantResolver) -> list[dict]:
    """Return copied match rows with non-destructive resolved participant fields."""
    enriched = []
    for match in matches:
        row = dict(match)
        home = resolver.resolve(row.get("home_source"))
        away = resolver.resolve(row.get("away_source"))
        row["home_participant"] = home.as_dict()
        row["away_participant"] = away.as_dict()
        row["home_team_id"] = home.team_id
        row["away_team_id"] = away.team_id
        row["home_team_name"] = home.team_name
        row["away_team_name"] = away.team_name
        enriched.append(row)
    return enriched
