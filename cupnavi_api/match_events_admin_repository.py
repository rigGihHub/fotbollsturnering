"""Organizer-scoped player match-event reads/writes for the Next admin.

This restores the Streamlit Matchhändelser domain surface without importing any
Streamlit code. Persisted participant sources remain symbolic; resolved team
identity is derived through the shared participant resolver.
"""
from __future__ import annotations

from cupnavi_core.rules import validate_match_event_totals

from .admin_repository import _has_tournament_access
from .participant_resolution_repository import tournament_participant_resolver
from .repository import all_rows, connect, one

EVENT_FIELDS = ("goals", "assists", "yellow_cards", "red_cards")


def _event_values(row):
    row = row or {}
    return {field: max(0, int(row.get(field) or 0)) for field in EVENT_FIELDS}


def _tournament(tournament_id: int):
    return one("SELECT * FROM tournaments WHERE id=?", (int(tournament_id),))


def _resolved_match(tournament_id: int, match_id: int):
    tournament = _tournament(tournament_id)
    if not tournament:
        return None
    match = one("SELECT * FROM matches WHERE id=? AND tournament_id=?", (int(match_id), int(tournament_id)))
    if not match:
        return None
    resolver = tournament_participant_resolver(tournament)
    home = resolver.resolve(match.get("home_source"))
    away = resolver.resolve(match.get("away_source"))
    row = dict(match)
    row["home_team_id"] = home.team_id
    row["away_team_id"] = away.team_id
    row["home_team_name"] = home.team_name
    row["away_team_name"] = away.team_name
    row["participants_resolved"] = bool(home.resolved and away.resolved)
    return row


def admin_event_matches(account_id: int, tournament_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    tournament = _tournament(tournament_id)
    if not tournament:
        return None
    resolver = tournament_participant_resolver(tournament)
    rows = all_rows(
        """SELECT * FROM matches WHERE tournament_id=?
           AND home_score IS NOT NULL AND away_score IS NOT NULL
           ORDER BY CASE WHEN scheduled_start IS NULL THEN 1 ELSE 0 END,
                    scheduled_start DESC,id DESC""",
        (int(tournament_id),),
    )
    matches = []
    for match in rows:
        home = resolver.resolve(match.get("home_source"))
        away = resolver.resolve(match.get("away_source"))
        if not home.resolved or not away.resolved:
            continue
        matches.append({
            "id": int(match["id"]),
            "stage": match.get("stage"),
            "match_no": match.get("match_no"),
            "scheduled_start": match.get("scheduled_start"),
            "home_team_id": int(home.team_id),
            "away_team_id": int(away.team_id),
            "home_team_name": home.team_name,
            "away_team_name": away.team_name,
            "home_score": int(match.get("home_score") or 0),
            "away_score": int(match.get("away_score") or 0),
        })
    return {"matches": matches, "count": len(matches)}


def admin_match_events(account_id: int, tournament_id: int, match_id: int):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    match = _resolved_match(tournament_id, match_id)
    if not match or not match["participants_resolved"]:
        return None
    if match.get("home_score") is None or match.get("away_score") is None:
        raise ValueError("Matchhändelser kan registreras först när ett resultat finns")

    teams = []
    for side in ("home", "away"):
        team_id = int(match[f"{side}_team_id"])
        players = all_rows(
            "SELECT id,team_id,name,player_number FROM players WHERE team_id=? ORDER BY player_number,name,id",
            (team_id,),
        )
        stats = {
            int(row["player_id"]): row
            for row in all_rows(
                """SELECT pms.* FROM player_match_stats pms
                   JOIN players p ON p.id=pms.player_id
                   WHERE pms.match_id=? AND p.team_id=?""",
                (int(match_id), team_id),
            )
        }
        player_rows = []
        for player in players:
            values = _event_values(stats.get(int(player["id"])))
            player_rows.append({
                "id": int(player["id"]),
                "name": player.get("name") or f"Spelare {player['id']}",
                "player_number": player.get("player_number"),
                **values,
            })
        teams.append({
            "side": side,
            "team_id": team_id,
            "team_name": match[f"{side}_team_name"],
            "team_score": int(match[f"{side}_score"] or 0),
            "players": player_rows,
            "registered_goals": sum(row["goals"] for row in player_rows),
            "registered_assists": sum(row["assists"] for row in player_rows),
        })

    tournament = _tournament(tournament_id) or {}
    return {
        "match": {
            "id": int(match["id"]),
            "stage": match.get("stage"),
            "match_no": match.get("match_no"),
            "scheduled_start": match.get("scheduled_start"),
            "home_team_name": match["home_team_name"],
            "away_team_name": match["away_team_name"],
            "match_status": match.get("match_status"),
            "home_score": int(match["home_score"] or 0),
            "away_score": int(match["away_score"] or 0),
        },
        "enabled": {
            "assists": bool(tournament.get("enable_assist_leaderboard", 1)),
            "cards": bool(tournament.get("enable_card_statistics", 1)),
        },
        "teams": teams,
    }


def update_player_match_events(account_id: int, tournament_id: int, match_id: int, player_id: int, values: dict):
    if not _has_tournament_access(account_id, tournament_id):
        return None
    detail = admin_match_events(account_id, tournament_id, match_id)
    if detail is None:
        return None

    team_payload = next(
        (team for team in detail["teams"] if any(int(player["id"]) == int(player_id) for player in team["players"])),
        None,
    )
    if team_payload is None:
        raise ValueError("Spelaren tillhör inte något av lagen i matchen")

    current = one(
        "SELECT * FROM player_match_stats WHERE match_id=? AND player_id=?",
        (int(match_id), int(player_id)),
    )
    current_values = _event_values(current)
    expected = values.get("expected") or {}
    expected_values = {field: max(0, int(expected.get(field) or 0)) for field in EVENT_FIELDS}
    if expected_values != current_values:
        raise RuntimeError("Matchhändelsen har ändrats av någon annan. Ladda om matchen och försök igen.")

    next_values = {field: max(0, int(values.get(field) or 0)) for field in EVENT_FIELDS}
    total_goals = 0
    total_assists = 0
    for player in team_payload["players"]:
        row_values = next_values if int(player["id"]) == int(player_id) else _event_values(player)
        total_goals += row_values["goals"]
        total_assists += row_values["assists"]
    validation = validate_match_event_totals(team_payload["team_score"], total_goals, total_assists)
    if not validation["ok"]:
        raise ValueError(" ".join(validation["errors"]))

    with connect() as con:
        if current:
            cursor = con.execute(
                """UPDATE player_match_stats
                   SET goals=?,assists=?,yellow_cards=?,red_cards=?
                   WHERE match_id=? AND player_id=?
                     AND goals=? AND assists=? AND yellow_cards=? AND red_cards=?""",
                (
                    next_values["goals"], next_values["assists"],
                    next_values["yellow_cards"], next_values["red_cards"],
                    int(match_id), int(player_id),
                    current_values["goals"], current_values["assists"],
                    current_values["yellow_cards"], current_values["red_cards"],
                ),
            )
            if getattr(cursor, "rowcount", 1) == 0:
                raise RuntimeError("Matchhändelsen har ändrats av någon annan. Ladda om matchen och försök igen.")
        else:
            try:
                con.execute(
                    """INSERT INTO player_match_stats(match_id,player_id,goals,assists,yellow_cards,red_cards)
                       VALUES(?,?,?,?,?,?)""",
                    (
                        int(match_id), int(player_id), next_values["goals"], next_values["assists"],
                        next_values["yellow_cards"], next_values["red_cards"],
                    ),
                )
            except Exception as exc:
                # A concurrent first write may have created the row after our read.
                latest = one(
                    "SELECT * FROM player_match_stats WHERE match_id=? AND player_id=?",
                    (int(match_id), int(player_id)),
                )
                if latest is not None:
                    raise RuntimeError("Matchhändelsen har ändrats av någon annan. Ladda om matchen och försök igen.") from exc
                raise
        commit = getattr(con, "commit", None)
        if callable(commit):
            commit()
    return admin_match_events(account_id, tournament_id, match_id)
