"""Pure calculations for compact public tournament highlights."""
from __future__ import annotations

from cupnavi_core.public_competition import calculate_group_table


def snapshot_table_bundle(teams, matches, *, points_win=3, points_draw=1, points_loss=0, table_tiebreak="Målskillnad först"):
    """Build the minimal table bundle from an already-loaded public snapshot.

    This deliberately avoids database reads on the public Matches page.
    """
    teams = [dict(row) for row in (teams or [])]
    matches = [dict(row) for row in (matches or [])]
    group_ids = sorted({
        int(row.get("group_id"))
        for row in matches
        if row.get("group_id") is not None
        and str(row.get("stage") or "") == "Gruppspel"
        and row.get("home_score") is not None
        and row.get("away_score") is not None
    })
    groups = [{"id": group_id} for group_id in group_ids]
    tables = {}
    for group_id in group_ids:
        group_teams = [row for row in teams if row.get("group_id") is not None and int(row.get("group_id")) == group_id]
        group_matches = [
            row for row in matches
            if row.get("group_id") is not None
            and int(row.get("group_id")) == group_id
            and str(row.get("stage") or "") == "Gruppspel"
            and row.get("home_score") is not None
            and row.get("away_score") is not None
        ]
        rows = calculate_group_table(
            group_teams, group_matches,
            points_win=int(points_win),
            points_draw=int(points_draw),
            points_loss=int(points_loss),
            table_tiebreak=str(table_tiebreak or "Målskillnad först"),
        )
        tables[group_id] = [
            (row["team_id"], {key: value for key, value in row.items() if key not in {"team_id", "position"}})
            for row in rows
        ]
    return {"groups": groups, "tables": tables}


def competition_highlights(table_bundle, player_rows=None, *, scorer_enabled=True, assist_enabled=True):
    """Return compact, tie-aware highlight data for the public match overview.

    Team highlights use completed group-stage matches only, because standings points
    and goals conceded are only comparable inside the table model. Individual
    leaders use the same ordering semantics as the existing public leaderboards.
    """
    player_rows = [dict(row) for row in (player_rows or [])]
    table_rows = []
    for group in table_bundle.get("groups", []):
        group_id = int(group["id"])
        for team_id, stats in table_bundle.get("tables", {}).get(group_id, []):
            row = dict(stats)
            row["team_id"] = int(team_id)
            table_rows.append(row)

    played_team_rows = [row for row in table_rows if int(row.get("S") or 0) > 0]
    result = {}

    if played_team_rows:
        max_points = max(int(row.get("P") or 0) for row in played_team_rows)
        point_leaders = sorted(
            [row for row in played_team_rows if int(row.get("P") or 0) == max_points],
            key=lambda row: (-(int(row.get("MS") or 0)), -(int(row.get("GM") or 0)), str(row.get("Lag") or "").lower()),
        )
        result["points"] = {
            "names": [str(row.get("Lag") or "") for row in point_leaders],
            "value": max_points,
        }

        min_conceded = min(int(row.get("IM") or 0) for row in played_team_rows)
        defensive_leaders = sorted(
            [row for row in played_team_rows if int(row.get("IM") or 0) == min_conceded],
            key=lambda row: (-(int(row.get("S") or 0)), str(row.get("Lag") or "").lower()),
        )
        result["defence"] = {
            "names": [str(row.get("Lag") or "") for row in defensive_leaders],
            "value": min_conceded,
        }

    if scorer_enabled:
        goal_rows = [row for row in player_rows if int(row.get("goals") or 0) > 0]
        goal_rows.sort(
            key=lambda row: (
                -int(row.get("goals") or 0),
                -int(row.get("assists") or 0),
                str(row.get("player_name") or "").lower(),
            )
        )
        if goal_rows:
            leader = goal_rows[0]
            result["scorer"] = {
                "player": str(leader.get("player_name") or ""),
                "team": str(leader.get("team_name") or ""),
                "value": int(leader.get("goals") or 0),
            }

    if assist_enabled:
        assist_rows = [row for row in player_rows if int(row.get("assists") or 0) > 0]
        assist_rows.sort(
            key=lambda row: (
                -int(row.get("assists") or 0),
                -int(row.get("goals") or 0),
                str(row.get("player_name") or "").lower(),
            )
        )
        if assist_rows:
            leader = assist_rows[0]
            result["assist"] = {
                "player": str(leader.get("player_name") or ""),
                "team": str(leader.get("team_name") or ""),
                "value": int(leader.get("assists") or 0),
            }

    return result
