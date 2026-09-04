"""Read-only public match overview queries.

Kept independent from Streamlit/session state so the SQL can be tested in
isolation and the app entrypoint only coordinates UI/session concerns.
"""
from __future__ import annotations

from typing import Any


def fetch_public_scorer_leader(con: Any, *, tournament_id: int) -> list[dict[str, Any]]:
    """Return only the current top scorer for the public Matches summary.

    This intentionally avoids the visitor-session aggregate used by the older
    combined overview snapshot. The Matches page no longer renders visitor
    counts, so asking the database for them on every live cup view was wasted
    work.
    """
    row = con.execute(
        """SELECT CASE WHEN COALESCE(p.is_protected,0)=1 THEN 'Skyddad spelare' ELSE p.name END AS player_name,
                  t.name AS team_name, SUM(s.goals) AS goals, SUM(s.assists) AS assists
           FROM player_match_stats s
           JOIN players p ON p.id=s.player_id
           JOIN teams t ON t.id=p.team_id
           JOIN matches m ON m.id=s.match_id
           WHERE m.tournament_id=?
           GROUP BY p.id,p.name,p.is_protected,t.name
           HAVING SUM(s.goals)>0
           ORDER BY SUM(s.goals) DESC, SUM(s.assists) DESC, LOWER(p.name) ASC
           LIMIT 1""",
        (int(tournament_id),),
    ).fetchone()
    if row is None:
        return []

    def value(key: str, index: int):
        try:
            return row[key]
        except (TypeError, KeyError, IndexError):
            return row[index]

    return [{
        "player_name": value("player_name", 0),
        "team_name": value("team_name", 1),
        "goals": int(value("goals", 2) or 0),
        "assists": int(value("assists", 3) or 0),
    }]


def fetch_public_match_overview(con: Any, *, tournament_id: int, cutoff: str, session_token: str,
                                scorer_enabled: bool = True, assist_enabled: bool = True) -> dict[str, Any]:
    row = con.execute(
        """WITH agg AS (
               SELECT CASE WHEN COALESCE(players.is_protected,0)=1 THEN 'Skyddad spelare' ELSE players.name END AS player_name,
                      teams.name AS team_name, SUM(s.goals) AS goals, SUM(s.assists) AS assists
               FROM player_match_stats s
               JOIN players ON players.id=s.player_id
               JOIN teams ON teams.id=players.team_id
               JOIN matches ON matches.id=s.match_id
               WHERE matches.tournament_id=?
               GROUP BY players.id,players.name,players.is_protected,teams.name
           ), scorer AS (
               SELECT player_name,team_name,goals,assists FROM agg
               WHERE ?=1 AND goals>0
               ORDER BY goals DESC, assists DESC, LOWER(player_name) ASC LIMIT 1
           ), assister AS (
               SELECT player_name,team_name,goals,assists FROM agg
               WHERE ?=1 AND assists>0
               ORDER BY assists DESC, goals DESC, LOWER(player_name) ASC LIMIT 1
           )
           SELECT
               (SELECT COUNT(*) FROM visitor_sessions
                WHERE tournament_id=? AND last_seen>=? AND session_token<>?) AS visitor_count,
               (SELECT player_name FROM scorer) AS scorer_player,
               (SELECT team_name FROM scorer) AS scorer_team,
               (SELECT goals FROM scorer) AS scorer_goals,
               (SELECT assists FROM scorer) AS scorer_assists,
               (SELECT player_name FROM assister) AS assist_player,
               (SELECT team_name FROM assister) AS assist_team,
               (SELECT goals FROM assister) AS assist_goals,
               (SELECT assists FROM assister) AS assist_assists""",
        (tournament_id, int(bool(scorer_enabled)), int(bool(assist_enabled)), tournament_id, cutoff, session_token),
    ).fetchone()

    if row is None:
        return {"visitor_count": 0, "leader_rows": []}

    def value(key: str, index: int):
        try:
            return row[key]
        except (TypeError, KeyError, IndexError):
            return row[index]

    leaders: list[dict[str, Any]] = []
    scorer_player = value("scorer_player", 1)
    scorer_team = value("scorer_team", 2)
    if scorer_player:
        leaders.append({"player_name": scorer_player, "team_name": scorer_team,
                        "goals": value("scorer_goals", 3), "assists": value("scorer_assists", 4)})
    assist_player = value("assist_player", 5)
    assist_team = value("assist_team", 6)
    if assist_player and not any(x["player_name"] == assist_player and x["team_name"] == assist_team for x in leaders):
        leaders.append({"player_name": assist_player, "team_name": assist_team,
                        "goals": value("assist_goals", 7), "assists": value("assist_assists", 8)})
    return {"visitor_count": int(value("visitor_count", 0) or 0), "leader_rows": leaders}


def fetch_public_match_events(con: Any, match_ids: list[int] | tuple[int, ...]) -> dict[int, list[Any]]:
    """Return goal/red-card event rows grouped by visible public match id."""
    normalized_ids = [int(match_id) for match_id in match_ids if int(match_id) > 0]
    if not normalized_ids:
        return {}
    placeholders = ",".join("?" for _ in normalized_ids)
    rows = con.execute(
        f"""SELECT s.match_id, p.name AS player_name, COALESCE(p.is_protected,0) AS is_protected,
                   t.id AS team_id, t.name AS team_name, s.goals, s.red_cards
            FROM player_match_stats s
            JOIN players p ON p.id=s.player_id
            JOIN teams t ON t.id=p.team_id
            WHERE s.match_id IN ({placeholders})
              AND (s.goals > 0 OR s.red_cards > 0)
            ORDER BY s.match_id,p.name""",
        tuple(normalized_ids),
    ).fetchall()
    grouped: dict[int, list[Any]] = {}
    event_columns = (
        "match_id", "player_name", "is_protected", "team_id",
        "team_name", "goals", "red_cards",
    )
    for row in rows:
        # SQLite rows support named access, while libSQL/Turso can return plain
        # positional tuples. Normalize at the repository boundary so the public
        # presentation layer never depends on a specific DB row implementation.
        normalized: dict[str, Any] = {}
        for index, column in enumerate(event_columns):
            try:
                value = row[column]
            except (TypeError, KeyError, IndexError):
                try:
                    value = row[index]
                except (TypeError, KeyError, IndexError):
                    value = None
            normalized[column] = value

        try:
            match_id = int(normalized["match_id"])
        except (TypeError, ValueError):
            continue
        grouped.setdefault(match_id, []).append(normalized)
    return grouped
