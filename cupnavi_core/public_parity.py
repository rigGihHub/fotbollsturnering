"""Compare public product data between legacy Streamlit semantics and API/PWA payloads."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from .public_competition import calculate_group_table, team_competition_summary

@dataclass
class ParityResult:
    ok: bool
    checks: dict[str,bool]
    details: list[str]

def _canonical_match(row: dict) -> tuple:
    return (
        int(row["id"]),
        str(row.get("stage") or ""),
        row.get("group_id"),
        row.get("bracket_id"),
        str(row.get("home_source") or ""),
        str(row.get("away_source") or ""),
        str(row.get("scheduled_start") or ""),
        row.get("pitch_number"),
        row.get("home_score"),
        row.get("away_score"),
        row.get("home_penalties"),
        row.get("away_penalties"),
    )

def compare_public_payloads(*, tournament:dict, teams:list[dict], groups:list[dict],
                            legacy_matches:list[dict], api_matches:list[dict],
                            legacy_brackets:list[dict], api_brackets:list[dict]) -> ParityResult:
    checks={}
    details=[]

    legacy_match_set=[_canonical_match(m) for m in legacy_matches]
    api_match_set=[_canonical_match(m) for m in api_matches]
    checks["matches"]=legacy_match_set==api_match_set
    if not checks["matches"]:
        details.append(f"matches differ: legacy={len(legacy_match_set)} api={len(api_match_set)}")

    # Table parity is checked using the single shared competition engine over
    # the same group teams/matches. If both frontends call this engine they must agree.
    standings_ok=True
    for group in groups:
        gid=int(group["id"])
        group_teams=[t for t in teams if int(t.get("group_id") or 0)==gid]
        group_matches=[m for m in legacy_matches if int(m.get("group_id") or 0)==gid and m.get("stage")=="Gruppspel"]
        a=calculate_group_table(
            group_teams,group_matches,
            points_win=int(tournament.get("points_win") or 0),
            points_draw=int(tournament.get("points_draw") or 0),
            points_loss=int(tournament.get("points_loss") or 0),
            table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
        )
        b=calculate_group_table(
            group_teams,[m for m in api_matches if int(m.get("group_id") or 0)==gid and m.get("stage")=="Gruppspel"],
            points_win=int(tournament.get("points_win") or 0),
            points_draw=int(tournament.get("points_draw") or 0),
            points_loss=int(tournament.get("points_loss") or 0),
            table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
        )
        if a!=b:
            standings_ok=False
            details.append(f"standings differ for group {gid}")
    checks["standings"]=standings_ok

    def canon_brackets(items):
        result=[]
        for b in items:
            result.append((
                int(b["id"]),str(b.get("name") or ""),int(b.get("size") or 0),
                tuple(_canonical_match(m) for m in b.get("matches",[]))
            ))
        return result
    checks["playoffs"]=canon_brackets(legacy_brackets)==canon_brackets(api_brackets)
    if not checks["playoffs"]:
        details.append("playoff brackets differ")

    # Min cup parity for every team, using the exact same shared summary engine.
    by_group={}
    for group in groups:
        gid=int(group["id"])
        group_teams=[t for t in teams if int(t.get("group_id") or 0)==gid]
        group_matches=[m for m in legacy_matches if int(m.get("group_id") or 0)==gid and m.get("stage")=="Gruppspel"]
        by_group[gid]=calculate_group_table(
            group_teams,group_matches,
            points_win=int(tournament.get("points_win") or 0),
            points_draw=int(tournament.get("points_draw") or 0),
            points_loss=int(tournament.get("points_loss") or 0),
            table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
        )
    my_cup_ok=True
    for team in teams:
        tid=int(team["id"]); gid=team.get("group_id")
        legacy_summary=team_competition_summary(tid,legacy_matches,by_group,gid)
        api_summary=team_competition_summary(tid,api_matches,by_group,gid)
        # Ignore object identity; compare stable business fields.
        keys=("matches","played","group_position")
        if any(legacy_summary[k]!=api_summary[k] for k in keys):
            my_cup_ok=False
            details.append(f"team summary differs for team {tid}")
    checks["my_cup"]=my_cup_ok

    return ParityResult(ok=all(checks.values()),checks=checks,details=details)
