"""CupNavi API for the public PWA and authenticated organizer admin."""
from __future__ import annotations

import hashlib
import os
import time

from fastapi import FastAPI, Header, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cupnavi_core.version import APP_VERSION
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary
from cupnavi_core.rate_limit import consume_rate_limit
from .admin_auth import issue_session, normalize_email, verify_session
from .admin_repository import (
    admin_cupinfo,
    admin_teams,
    authenticate_organizer,
    create_team,
    delete_team,
    organizer_account,
    organizer_tournaments,
    update_cupinfo,
    update_team,
)
from .group_admin_repository import (
    admin_groups,
    assign_team_group,
    create_group,
    delete_group,
    update_group,
)
from .repository import (
    public_tournament, public_teams, public_groups, public_matches, public_venue_points,
    public_notifications, public_brackets, public_snapshot, public_statistics,
    backend_name, standings_inputs, database_probe, connect,
)

app=FastAPI(title="CupNavi API",version=APP_VERSION,docs_url="/docs",redoc_url=None)

_cors_origins=[
    item.strip() for item in os.getenv("CUPNAVI_PWA_ORIGINS","*").split(",") if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins or ["*"],
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type"],
)


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class CupInfoUpdate(BaseModel):
    name: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    organizer: str | None = None
    arena_address: str | None = None
    organizer_phone: str | None = None
    feedback_email: str | None = None
    public_information: str | None = None


class TeamWrite(BaseModel):
    name: str | None = None
    age_class: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None


class GroupWrite(BaseModel):
    name: str | None = None
    age_class: str | None = None


class TeamGroupWrite(BaseModel):
    group_id: int | None = None


def _model_values(model: BaseModel) -> dict:
    """Support both Pydantic v1 and v2 without pinning CupNavi to one major."""
    model_dump=getattr(model,"model_dump",None)
    if callable(model_dump):
        return model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


@app.middleware("http")
async def add_server_timing(request:Request, call_next):
    started=time.perf_counter()
    response=await call_next(request)
    elapsed_ms=(time.perf_counter()-started)*1000
    response.headers["Server-Timing"]=f"app;dur={elapsed_ms:.1f}"
    response.headers["X-CupNavi-Process-Ms"]=f"{elapsed_ms:.1f}"
    return response


def _admin_identity(authorization: str | None):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401,detail="Authentication required")
    payload=verify_session(authorization.split(" ",1)[1].strip())
    if not payload:
        raise HTTPException(status_code=401,detail="Session expired or invalid")
    account=organizer_account(int(payload["sub"]))
    if not account:
        raise HTTPException(status_code=401,detail="Organizer account unavailable")
    return account


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


@app.post("/api/admin/session")
def admin_login(payload:AdminLoginRequest):
    email=normalize_email(payload.email)
    subject_hash=hashlib.sha256(email.encode("utf-8")).hexdigest()
    with connect() as con:
        allowed,retry_after,_=consume_rate_limit(
            con,
            scope="admin_login",
            subject_hash=subject_hash,
            limit=10,
            window_seconds=900,
        )
        commit=getattr(con,"commit",None)
        if callable(commit):
            commit()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="För många inloggningsförsök",
            headers={"Retry-After":str(retry_after)},
        )
    account=authenticate_organizer(email,payload.password)
    if not account:
        raise HTTPException(status_code=401,detail="Fel e-postadress eller lösenord")
    try:
        token=issue_session(account)
    except RuntimeError as exc:
        raise HTTPException(status_code=503,detail="Admin sessions are not configured") from exc
    return {"token":token,"account":account,"cups":organizer_tournaments(int(account["id"]))}


@app.get("/api/admin/session")
def admin_session(authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    return {"account":account,"cups":organizer_tournaments(int(account["id"]))}


@app.get("/api/admin/cups/{tournament_id}/cupinfo")
def get_admin_cupinfo(tournament_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    cupinfo=admin_cupinfo(int(account["id"]),tournament_id)
    if not cupinfo:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return cupinfo


@app.put("/api/admin/cups/{tournament_id}/cupinfo")
def put_admin_cupinfo(tournament_id:int,payload:CupInfoUpdate,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        cupinfo=update_cupinfo(int(account["id"]),tournament_id,_model_values(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not cupinfo:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return cupinfo


@app.get("/api/admin/cups/{tournament_id}/teams")
def get_admin_teams(tournament_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    teams=admin_teams(int(account["id"]),tournament_id)
    if teams is None:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return {"teams":teams}


@app.post("/api/admin/cups/{tournament_id}/teams",status_code=201)
def post_admin_team(tournament_id:int,payload:TeamWrite,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        team=create_team(int(account["id"]),tournament_id,_model_values(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not team:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return team


@app.put("/api/admin/cups/{tournament_id}/teams/{team_id}")
def put_admin_team(tournament_id:int,team_id:int,payload:TeamWrite,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        team=update_team(int(account["id"]),tournament_id,team_id,_model_values(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not team:
        raise HTTPException(status_code=404,detail="Lag saknas eller åtkomst nekas")
    return team


@app.delete("/api/admin/cups/{tournament_id}/teams/{team_id}")
def remove_admin_team(tournament_id:int,team_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        deleted=delete_team(int(account["id"]),tournament_id,team_id)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404,detail="Lag saknas eller åtkomst nekas")
    return {"deleted":True,"team":deleted}


@app.get("/api/admin/cups/{tournament_id}/groups")
def get_admin_groups(tournament_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    groups=admin_groups(int(account["id"]),tournament_id)
    if groups is None:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return {"groups":groups}


@app.post("/api/admin/cups/{tournament_id}/groups",status_code=201)
def post_admin_group(tournament_id:int,payload:GroupWrite,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        group=create_group(int(account["id"]),tournament_id,_model_values(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not group:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return group


@app.put("/api/admin/cups/{tournament_id}/groups/{group_id}")
def put_admin_group(tournament_id:int,group_id:int,payload:GroupWrite,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        group=update_group(int(account["id"]),tournament_id,group_id,_model_values(payload))
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not group:
        raise HTTPException(status_code=404,detail="Grupp saknas eller åtkomst nekas")
    return group


@app.delete("/api/admin/cups/{tournament_id}/groups/{group_id}")
def remove_admin_group(tournament_id:int,group_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        deleted=delete_group(int(account["id"]),tournament_id,group_id)
    except ValueError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404,detail="Grupp saknas eller åtkomst nekas")
    return {"deleted":True,"group":deleted}


@app.put("/api/admin/cups/{tournament_id}/teams/{team_id}/group")
def put_admin_team_group(tournament_id:int,team_id:int,payload:TeamGroupWrite,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        team=assign_team_group(int(account["id"]),tournament_id,team_id,payload.group_id)
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not team:
        raise HTTPException(status_code=404,detail="Lag saknas eller åtkomst nekas")
    return team


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


@app.get("/api/public/cups/{public_key}/statistics")
def statistics(public_key:str):
    tournament=public_tournament(public_key)
    if not tournament:
        raise HTTPException(status_code=404,detail="Cup not found or not published")
    payload=public_statistics(int(tournament["id"]))
    return {
        "enabled":{
            "scorers":bool(tournament.get("show_scorer_stats")),
            "assists":bool(tournament.get("show_assist_stats")),
            "cards":bool(tournament.get("show_card_stats")),
            "fairness":bool(tournament.get("show_fairness")),
        },
        **payload,
    }


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
    summary=team_competition_summary(team_id,public_matches(tid),standings_by_group,team.get("group_id"))
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
