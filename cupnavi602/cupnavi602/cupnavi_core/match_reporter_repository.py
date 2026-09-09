"""Read-only query contracts for the Match Reporter workspace.

Persistence and optimistic-locking writes deliberately remain in ``app.py``.
The caller supplies its existing ``query_all`` function so query caching and
performance accounting stay at the application boundary.
"""
from __future__ import annotations

from typing import Any, Callable

QueryAll = Callable[[str, tuple[Any, ...]], list[Any]]


def fetch_scheduled_matches(query_all: QueryAll, tournament_id: int) -> list[Any]:
    return query_all(
        """SELECT * FROM matches
           WHERE tournament_id=? AND scheduled_start IS NOT NULL
           ORDER BY scheduled_start,pitch_number,id""",
        (int(tournament_id),),
    )


def fetch_completed_matches(query_all: QueryAll, tournament_id: int) -> list[Any]:
    return query_all(
        """SELECT * FROM matches
           WHERE tournament_id=? AND home_score IS NOT NULL AND away_score IS NOT NULL
           ORDER BY scheduled_start DESC,id DESC""",
        (int(tournament_id),),
    )


def fetch_teams(query_all: QueryAll, tournament_id: int) -> list[Any]:
    return query_all(
        "SELECT id,name FROM teams WHERE tournament_id=? ORDER BY name",
        (int(tournament_id),),
    )


def fetch_match_team_players(query_all: QueryAll, match_id: int, team_id: int) -> dict[str, Any]:
    registered = query_all(
        """SELECT p.* FROM players p
           JOIN match_rosters mr ON mr.player_id=p.id
           WHERE mr.match_id=? AND mr.team_id=? AND p.team_id=?
           ORDER BY p.player_number,p.name""",
        (int(match_id), int(team_id), int(team_id)),
    )
    players = registered or query_all(
        "SELECT * FROM players WHERE team_id=? ORDER BY player_number,name",
        (int(team_id),),
    )
    return {"registered": registered, "players": players}


def fetch_player_match_stats(query_all: QueryAll, match_id: int, team_id: int) -> list[Any]:
    return query_all(
        """SELECT * FROM player_match_stats
           WHERE match_id=? AND player_id IN
           (SELECT id FROM players WHERE team_id=?)""",
        (int(match_id), int(team_id)),
    )


def fetch_referees(query_all: QueryAll, tournament_id: int) -> list[Any]:
    return query_all(
        "SELECT * FROM referees WHERE tournament_id=? ORDER BY name",
        (int(tournament_id),),
    )


def fetch_referee_assignments(query_all: QueryAll, tournament_id: int, referee_id: int) -> list[Any]:
    return query_all(
        """SELECT * FROM matches WHERE tournament_id=? AND referee_id=? AND scheduled_start IS NOT NULL
           ORDER BY scheduled_start,pitch_number,id""",
        (int(tournament_id), int(referee_id)),
    )


def fetch_referee_acknowledged_match_ids(query_all: QueryAll, tournament_id: int, referee_id: int) -> set[int]:
    rows = query_all(
        "SELECT match_id FROM referee_acknowledgements WHERE tournament_id=? AND referee_id=?",
        (int(tournament_id), int(referee_id)),
    )
    return {int(row["match_id"]) for row in rows}
