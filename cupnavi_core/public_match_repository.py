"""Read-only public match overview queries.

Kept independent from Streamlit/session state so the SQL can be tested in
isolation and the app entrypoint only coordinates UI/session concerns.
"""
from __future__ import annotations

from typing import Any


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
    for row in rows:
        try:
            match_id = int(row["match_id"])
        except (TypeError, KeyError, IndexError):
            match_id = int(row[0])
        grouped.setdefault(match_id, []).append(row)
    return grouped
