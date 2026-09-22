"""CupNavi API for the public PWA and authenticated organizer admin."""
from __future__ import annotations

import hashlib
import os
import re
import time

from fastapi import FastAPI, Header, HTTPException, Response, Request
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from cupnavi_core.version import APP_VERSION
from cupnavi_core.ai_kit_suggestion import suggest_team_kit
from cupnavi_core.public_competition import calculate_group_table, team_competition_summary
from cupnavi_core.rate_limit import consume_rate_limit
from .admin_auth import issue_session, normalize_email, verify_session
from .logo_cache import cached_logo_path, cache_verified_logo
from .admin_repository import (
    admin_cupinfo,
    admin_teams,
    authenticate_organizer,
    create_team,
    delete_team,
    organizer_account,
    organizer_tournaments,
    purge_trashed_tournaments,
    restore_tournament,
    trashed_tournaments,
    trash_tournament,
    update_cupinfo,
    update_team,
    ConcurrentUpdateError,
)
from .group_admin_repository import (
    admin_groups,
    assign_team_group,
    create_group,
    delete_group,
    update_group,
)
from .participant_resolution_repository import public_bracket_resolution, resolve_public_snapshot
from .venue_admin_routes import register_venue_admin_routes
from .access_routes import register_access_routes
from .repository import (
    public_tournament, public_teams, public_groups, public_matches, public_venue_points,
    public_notifications, public_brackets, public_snapshot, public_statistics,
    backend_name, standings_inputs, database_probe, connect,
)

app=FastAPI(title="CupNavi API",version=APP_VERSION,docs_url="/docs",redoc_url=None)

_cors_origins=[
    item.strip() for item in os.getenv("CUPNAVI_PWA_ORIGINS","https://cupnavi-web.onrender.com,https://cup-navi.com,https://www.cup-navi.com").split(",") if item.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=False,
    allow_methods=["GET","POST","PUT","DELETE","OPTIONS"],
    allow_headers=["Authorization","Content-Type"],
)


@app.get("/api/assets/club-logos/{digest}")
def get_cached_club_logo(digest: str):
    path = cached_logo_path(digest)
    if path is None:
        # Render's local /tmp cache is ephemeral and can also differ between
        # instances. Rebuild a missing verified asset from the source URL
        # persisted with the team instead of leaving a permanent broken logo.
        try:
            with connect() as con:
                cursor = con.execute(
                    "SELECT logo_source_url FROM teams WHERE logo_url LIKE ? AND logo_source_url IS NOT NULL LIMIT 1",
                    (f"%/api/assets/club-logos/{digest}",),
                )
                columns = [item[0] for item in (cursor.description or [])]
                raw = cursor.fetchone()
            # SQLite rows allow numeric indexing, but the production Turso/libsql
            # adapter may return dict-like rows. Handle both representations.
            if raw is None:
                source_url = None
            elif isinstance(raw, dict):
                source_url = raw.get("logo_source_url")
            else:
                try:
                    source_url = raw[0]
                except (KeyError, TypeError):
                    source_url = dict(zip(columns, raw)).get("logo_source_url") if columns else None
            if source_url:
                restored_digest, _ = cache_verified_logo(str(source_url))
                if restored_digest == digest:
                    path = cached_logo_path(digest)
        except (ValueError, OSError):
            path = None
    if path is None:
        raise HTTPException(status_code=404, detail="Club logo not found")
    return FileResponse(path, headers={"Cache-Control": "public, max-age=86400, immutable"})

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
    arrangement_type: str | None = None
    show_public_weather: bool | None = None
    show_public_weather_configured: bool | None = None
    show_public_kits: bool | None = None
    show_public_away_kits: bool | None = None
    show_public_logos: bool | None = None
    expected_revision: int | None = None


class TeamWrite(BaseModel):
    name: str | None = None
    age_class: str | None = None
    primary_color: str | None = None
    secondary_color: str | None = None
    home_pattern: str | None = None
    home_color_2: str | None = None
    away_pattern: str | None = None
    away_color_2: str | None = None
    logo_url: str | None = None
    logo_source_url: str | None = None


class KitSearchRequest(BaseModel):
    team_name: str
    age_class: str | None = None
    search_hint: str | None = None
    resolved_club: str | None = None
    resolved_source_url: str | None = None
    search_focus: str = "kit"
    force_refresh: bool = False


class GroupWrite(BaseModel):
    name: str | None = None
    age_class: str | None = None


class TeamGroupWrite(BaseModel):
    group_id: int | None = None


class CupDeleteRequest(BaseModel):
    confirmed_name: str


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
    response.headers["X-Content-Type-Options"]="nosniff"
    response.headers["X-Frame-Options"]="DENY"
    response.headers["Referrer-Policy"]="strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"]="camera=(), microphone=(), geolocation=(), payment=()"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"]="max-age=31536000; includeSubDomains"
    if request.method in {"POST","PUT","DELETE"} and response.status_code < 400:
        match=re.match(r"^/api/admin/cups/(\d+)(?:/|$)",request.url.path)
        manually_logged=request.url.path.endswith("/cupinfo") or "/members" in request.url.path
        if match and not manually_logged:
            try:
                authorization=request.headers.get("authorization") or ""
                token=authorization.split(" ",1)[1] if authorization.lower().startswith("bearer ") else ""
                payload=verify_session(token)
                account=organizer_account(int(payload["sub"])) if payload else None
                if account:
                    tail=request.url.path.split(f"/cups/{match.group(1)}",1)[-1].strip("/") or "cup"
                    with connect() as con:
                        con.execute(
                            """INSERT INTO admin_activity(
                                   tournament_id,organizer_account_id,actor_email,action,entity_type,summary
                               ) VALUES(?,?,?,?,?,?)""",
                            (int(match.group(1)),None if int(account["id"])==0 else int(account["id"]),str(account.get("email") or "CupNavi Owner"),request.method.casefold(),tail.split("/",1)[0],f"{request.method} {tail}"),
                        )
                        commit=getattr(con,"commit",None)
                        if callable(commit):commit()
            except Exception:
                # Logging must never turn a completed tournament write into an API failure.
                pass
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
    if int(payload.get("sv") or 1) != int(account.get("session_version") or 1):
        raise HTTPException(status_code=401,detail="Session expired or invalid")
    return account


register_venue_admin_routes(app, _admin_identity)
register_access_routes(app, _admin_identity)


@app.get("/")
@app.head("/")
def root_health():
    return {"ok": True, "service": "cupnavi-api", "version": APP_VERSION}


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
        token=issue_session(organizer_account(int(account["id"])) or account)
    except RuntimeError as exc:
        raise HTTPException(status_code=503,detail="Admin sessions are not configured") from exc
    return {"token":token,"account":account,"cups":organizer_tournaments(int(account["id"]))}


@app.get("/api/admin/session")
def admin_session(authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    return {"account":account,"cups":organizer_tournaments(int(account["id"]))}


@app.get("/api/admin/trash")
def get_admin_trash(authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        cups=trashed_tournaments(int(account["id"]))
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    return {"cups":cups}


@app.delete("/api/admin/trash")
def empty_admin_trash(authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        deleted=purge_trashed_tournaments(int(account["id"]))
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    return {"emptied":True,"deleted":deleted,"trash":[]}


@app.post("/api/admin/trash/{tournament_id}/restore")
def restore_admin_cup(tournament_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        restored=restore_tournament(int(account["id"]),tournament_id)
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    if not restored:
        raise HTTPException(status_code=404,detail="Cupen finns inte i papperskorgen")
    return {
        "restored":True,
        "cup":restored,
        "cups":organizer_tournaments(int(account["id"])),
        "trash":trashed_tournaments(int(account["id"])),
    }


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
    except ConcurrentUpdateError as exc:
        raise HTTPException(status_code=409,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not cupinfo:
        raise HTTPException(status_code=404,detail="Cup not found or access denied")
    return cupinfo


@app.delete("/api/admin/cups/{tournament_id}")
def remove_admin_cup(tournament_id:int,payload:CupDeleteRequest,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    try:
        deleted=trash_tournament(int(account["id"]),tournament_id,payload.confirmed_name)
    except PermissionError as exc:
        raise HTTPException(status_code=403,detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404,detail="Cupen saknas eller har redan tagits bort")
    return {
        "deleted":True,
        "recoverable":True,
        "cup":deleted,
        "cups":organizer_tournaments(int(account["id"])),
    }


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


_FREE_CLUB_ASSETS = {
    "aik": {"club_match":"AIK Fotboll · Solna","home_pattern":"Helfärgad","home_color_1":"#111111","home_color_2":"#111111","away_pattern":"Helfärgad","away_color_1":"#FFFFFF","away_color_2":"#FFFFFF"},
    "hammarby": {"club_match":"Hammarby IF Fotboll · Stockholm","home_pattern":"Vertikala ränder","home_color_1":"#178344","home_color_2":"#FFFFFF","away_pattern":"Vertikala ränder","away_color_1":"#F4D03F","away_color_2":"#111111"},
    "örebro sk": {"club_match":"Örebro SK Fotboll · Örebro","home_pattern":"Helfärgad","home_color_1":"#FFFFFF","home_color_2":"#FFFFFF","away_pattern":"Helfärgad","away_color_1":"#111111","away_color_2":"#111111"},
}

def _free_club_asset_result(team_name:str, search_focus:str):
    key=" ".join(str(team_name or "").casefold().split())
    club=next((value for name,value in _FREE_CLUB_ASSETS.items() if key==name or key.startswith(name+" ")),None)
    if not club:
        return None
    # Built-in entries are conservative fallbacks: useful known kit presentation,
    # but never pretend that a crest or current-season evidence was web-verified.
    return {
        "found": search_focus != "logo", "confidence":"medium", "reason":"CupNavis kostnadsfria klubbregister.",
        **club, "home_sources":[], "away_sources":[], "sources":[],
        "home_evidence":"Känt klubbregister; kontrollera mot aktuellt ungdomslag vid behov.",
        "away_evidence":"Känt klubbregister; kontrollera aktuellt bortaställ vid behov.",
        "home_verified":False, "away_verified":False, "identity_status":"exact", "candidate_matches":[],
        "logo_url":"", "logo_source_url":"", "logo_verified":False, "club_match":club["club_match"],
        "cache_hit":False, "search_strategy":"Kostnadsfritt klubbregister", "search_attempts":0, "attempted_strategies":[]
    }


@app.post("/api/admin/cups/{tournament_id}/teams/kit-search")
def search_admin_team_kit(tournament_id:int,payload:KitSearchRequest,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    cupinfo=admin_cupinfo(int(account["id"]),tournament_id)
    if not cupinfo:
        raise HTTPException(status_code=404,detail="Cup saknas eller åtkomst nekas")
    api_key=os.getenv("OPENAI_API_KEY","").strip()
    free_result=_free_club_asset_result(payload.team_name,str(payload.search_focus or "kit"))
    # Prefer CupNavi's own free knowledge for known clubs. This avoids spending
    # paid AI credits on facts we already know and makes repeated cup setup stable.
    if free_result is not None and not payload.force_refresh:
        return free_result
    if not api_key:
        if free_result is not None:
            return free_result
        raise HTTPException(status_code=503,detail="Ingen kostnadsfri klubbträff hittades. Ange färger manuellt eller komplettera klubbregistret.")
    try:
        result = suggest_team_kit(
            payload.team_name,api_key,
            model=os.getenv("CUPNAVI_AI_KIT_MODEL","gpt-4.1-mini").strip() or "gpt-4.1-mini",
            location=str(cupinfo.get("arena_address") or ""),
            age_class=str(payload.age_class or ""),
            search_hint=str(payload.search_hint or ""),
            resolved_club=str(payload.resolved_club or ""),
            resolved_source_url=str(payload.resolved_source_url or ""),
            search_focus=str(payload.search_focus or "kit"),
            use_cache=not payload.force_refresh,
        )
        if result.get("logo_verified") and result.get("logo_url"):
            original_logo_url = str(result["logo_url"])
            try:
                digest, _ = cache_verified_logo(original_logo_url)
                api_public_base=os.getenv("CUPNAVI_API_PUBLIC_BASE","https://cupnavi-api.onrender.com").rstrip("/")
                result["logo_url"] = f"{api_public_base}/api/assets/club-logos/{digest}"
                result["logo_source_url"] = str(result.get("logo_source_url") or original_logo_url)
            except (ValueError, OSError):
                # Keep the verified source evidence, but do not return an
                # external image URL that may fail or block hotlinking.
                result["logo_url"] = ""
                result["logo_verified"] = False
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422,detail=str(exc)) from exc
    except RuntimeError as exc:
        raw_detail=" ".join(str(exc).split())[:500]
        print(f"[kit-search] upstream failure focus={payload.search_focus} team={payload.team_name!r}: {raw_detail}", flush=True)
        detail=raw_detail
        if "AI_RATE_LIMIT" in raw_detail or "rate_limit" in raw_detail.lower():
            retry_match=re.search(r"Vänta\s+(\d+)\s+sekunder", raw_detail, flags=re.I)
            headers={"Retry-After":retry_match.group(1)} if retry_match else None
            detail="AI_RATE_LIMIT: Söktjänsten är rate-limitad just nu. CupNavi stoppade sökningen för att skydda redan sparad data och undvika onödiga anrop."
            raise HTTPException(status_code=429,detail=detail,headers=headers) from exc
        if "timed out" in raw_detail.lower() or "timeout" in raw_detail.lower():
            detail=f"Tröjsökningen tog för lång tid. Teknisk detalj: {raw_detail}"
        elif "401" in raw_detail or "authentication" in raw_detail.lower():
            detail=f"Tröjsökningens anslutning är inte korrekt konfigurerad. Teknisk detalj: {raw_detail}"
        elif "credit_balance_exhausted" in raw_detail:
            if free_result is not None:
                return free_result
            detail="AI-krediterna är slut. CupNavi fortsätter utan betaltjänsten; välj färger manuellt för den här klubben tills den finns i det kostnadsfria klubbregistret."
        else:
            detail=f"Tröjsökningen kunde inte slutföras mot söktjänsten. Teknisk detalj: {raw_detail}"
        raise HTTPException(status_code=502,detail=detail) from exc


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
    return resolve_public_snapshot(snapshot)


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


@app.get("/api/admin/cups/{tournament_id}/preview")
def admin_cup_preview(tournament_id:int,authorization:str|None=Header(default=None)):
    account=_admin_identity(authorization)
    cupinfo=admin_cupinfo(int(account["id"]),tournament_id)
    if not cupinfo:
        raise HTTPException(status_code=404,detail="Cup saknas eller åtkomst nekas")
    snapshot=public_snapshot(str(tournament_id),include_unpublished=True)
    if not snapshot:
        raise HTTPException(status_code=404,detail="Cupen kunde inte förhandsgranskas")
    resolved=resolve_public_snapshot(snapshot)
    return {"cup":resolved,"standings":_standings_payload(resolved["tournament"])}


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
    brackets=public_brackets(int(tournament["id"]))
    return {
        "playoff_format":tournament.get("playoff_format"),
        "brackets":brackets,
        "participant_resolution":public_bracket_resolution(tournament,brackets),
    }


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
