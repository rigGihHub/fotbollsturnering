"""Standalone read-only public API for the future CupNavi PWA."""
from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query, Response, Request
import os, time
from fastapi.middleware.cors import CORSMiddleware
from cupnavi_core.version import APP_VERSION
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary
from .repository import (
    public_tournament, public_teams, public_groups, public_matches, public_venue_points,
    public_notifications, public_brackets, public_snapshot, backend_name, standings_inputs, database_probe
)

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

@app.middleware("http")
async def add_server_timing(request:Request, call_next):
    started=time.perf_counter()
    response=await call_next(request)
    elapsed_ms=(time.perf_counter()-started)*1000
    response.headers["Server-Timing"]=f"app;dur={elapsed_ms:.1f}"
    response.headers["X-CupNavi-Process-Ms"]=f"{elapsed_ms:.1f}"
    return response

@app.get("/health")
def health(response:Response):
    probe=database_probe()
    if not probe["ok"]:
        response.status_code=503
    return {
        "ok":bool(probe["ok"]),
        "version":APP_VERSION,
        "database_backend":backend_name(),
        "database_ok":bool(probe["ok"]),
        "database_latency_ms":probe["latency_ms"],
        "database_error":probe["error"],
    }

@app.get("/api/public/cups/{public_key}")
def cup(public_key:str):
    snapshot=public_snapshot(public_key)
    if not snapshot:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    return snapshot

def _standings_payload(tournament):
    result=[]
    groups,teams_by_group,matches_by_group=standings_inputs(int(tournament["id"]))
    for group in groups:
        group_id=int(group["id"])
        rows=calculate_group_table(
            teams_by_group.get(group_id,[]),
            matches_by_group.get(group_id,[]),
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
