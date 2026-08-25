"""Standalone read-only public API for the future CupNavi PWA."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query
import os
from fastapi.middleware.cors import CORSMiddleware
from cupnavi_core.version import APP_VERSION
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary
from .repository import public_tournament, public_teams, public_groups, public_matches, public_venue_points, public_notifications, group_teams, group_completed_matches, public_brackets, backend_name

app=FastAPI(title="CupNavi Public API",version=APP_VERSION,docs_url="/docs",redoc_url=None)

_cors_origins=[
    item.strip() for item in os.getenv("CUPNAVI_PWA_ORIGINS","*").split(",") if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"ok":True,"version":APP_VERSION,"database_backend":backend_name()}

@app.get("/api/public/cups/{public_key}")
def cup(public_key:str):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    tid=int(tournament["id"])
    return {
        "tournament":tournament,
        "teams":public_teams(tid),
        "groups":public_groups(tid),
        "matches":public_matches(tid),
        "venue_points":public_venue_points(tid),
    }

def _standings_payload(tournament):
    result=[]
    for group in public_groups(int(tournament["id"])):
        rows=calculate_group_table(
            group_teams(group["id"]),
            group_completed_matches(group["id"]),
            points_win=int(tournament.get("points_win") or 0),
            points_draw=int(tournament.get("points_draw") or 0),
            points_loss=int(tournament.get("points_loss") or 0),
            table_tiebreak=str(tournament.get("table_tiebreak") or "Målskillnad först"),
        )
        result.append({"group":group,"rows":rows})
    return result

@app.get("/api/public/cups/{public_key}/standings")
def standings(public_key:str):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    return {"groups":_standings_payload(tournament)}

@app.get("/api/public/cups/{public_key}/playoffs")
def playoffs(public_key:str):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    return {"playoff_format":tournament.get("playoff_format"),"brackets":public_brackets(int(tournament["id"]))}

@app.get("/api/public/cups/{public_key}/teams/{team_id}/summary")
def team_summary(public_key:str,team_id:int):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    tid=int(tournament["id"])
    teams=public_teams(tid)
    team=next((t for t in teams if int(t["id"])==int(team_id)),None)
    if not team:
        raise HTTPException(status_code=404,detail="Team not found")
    standings_rows=_standings_payload(tournament)
    standings_by_group={int(item["group"]["id"]):item["rows"] for item in standings_rows}
    summary=team_competition_summary(
        team_id,
        public_matches(tid),
        standings_by_group,
        team.get("group_id"),
    )
    return {"team":team,"summary":summary,"notifications":public_notifications(tid,team_id)}

@app.get("/api/public/cups/{public_key}/teams/{team_id}/notifications")
def team_notifications(public_key:str,team_id:int):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    tid=int(tournament["id"])
    team_ids={int(t["id"]) for t in public_teams(tid)}
    if int(team_id) not in team_ids:
        raise HTTPException(status_code=404,detail="Team not found")
    return {"notifications":public_notifications(tid,team_id)}
