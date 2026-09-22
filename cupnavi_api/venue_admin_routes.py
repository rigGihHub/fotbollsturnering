"""FastAPI route registration for organizer setup and schedule administration."""
from __future__ import annotations

import os
from datetime import date

from fastapi import File, Header, HTTPException, UploadFile
from pydantic import BaseModel
from .matchcamp_builder_repository import apply_matchcamp_pairing, matchcamp_pairing_proposal

from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents
from cupnavi_core.cup_document_creator_view import save_setup_import_snapshot
from .competition_admin_routes import register_competition_admin_routes
from .cup_create_repository import create_owner_tournament
from .initial_import_idempotency import apply_document_matches_idempotent
from .repository import connect
from .rules_admin_repository import admin_rules, update_rules
from .schedule_admin_repository import admin_schedule, confirm_current_schedule, update_match_schedule
from .schedule_proposal_repository import ProposalStaleError, admin_schedule_proposal, apply_schedule_proposal
from .venue_admin_repository import (
    admin_venues,
    update_pitch,
    update_pitch_window,
    update_venue_rules,
)


class CupCreateWrite(BaseModel):
    name: str
    start_date: str | None = None
    end_date: str | None = None


class InitialImportCommit(BaseModel):
    proposal: dict
    import_matches: bool = False
    fallback_date: str | None = None


class VenueRulesWrite(BaseModel):
    pitch_count: int | None = None
    first_match_time: str | None = None
    latest_kickoff_time: str | None = None
    synchronized_pitch_times: bool | None = None
    consider_pitch_travel: bool | None = None


class PitchWrite(BaseModel):
    name: str | None = None
    address: str | None = None


class PitchWindowWrite(BaseModel):
    start_time: str
    end_time: str
    confirmed: bool = True


class CompetitionRulesWrite(BaseModel):
    halves: int | None = None
    minutes_per_half: int | None = None
    halftime_minutes: int | None = None
    pitch_break_minutes: int | None = None
    minimum_team_rest_minutes: int | None = None
    avoid_consecutive_matches: bool | None = None
    consecutive_match_break_minutes: int | None = None
    points_win: int | None = None
    points_draw: int | None = None
    points_loss: int | None = None
    table_tiebreak: str | None = None


class MatchScheduleWrite(BaseModel):
    scheduled_start: str | None = None
    pitch_number: int | None = None


class ScheduleProposalApply(BaseModel):
    fingerprint: str


class MatchcampPairingWrite(BaseModel):
    matches_per_team: int
    fingerprint: str | None = None


def _model_values(model: BaseModel) -> dict:
    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def register_venue_admin_routes(app, admin_identity):
    @app.post("/api/admin/cups", status_code=201)
    def post_admin_cup(payload: CupCreateWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            cup = create_owner_tournament(int(account["id"]), _model_values(payload))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if not cup:
            raise HTTPException(status_code=500, detail="Cupen skapades men kunde inte läsas tillbaka")
        return cup

    @app.post("/api/admin/cup-import/analyze")
    async def analyze_admin_cup_import(
        files: list[UploadFile] = File(...),
        authorization: str | None = Header(default=None),
    ):
        """Review-first AI extraction used by the Next admin new-cup flow."""
        account = admin_identity(authorization)
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=503, detail="AI-importen är inte konfigurerad på servern")
        documents = []
        for upload in files:
            raw = await upload.read()
            documents.append((raw, upload.filename or "dokument", upload.content_type or ""))
        try:
            extracted = extract_cup_setup_from_documents(documents, api_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        extracted["source_name"] = ", ".join(upload.filename or "dokument" for upload in files)
        return extracted

    @app.post("/api/admin/cups/{tournament_id}/import/initial")
    def commit_initial_admin_import(
        tournament_id: int,
        payload: InitialImportCommit,
        authorization: str | None = Header(default=None),
    ):
        """Persist the reviewed first scan and optionally create its reviewed group-stage schedule."""
        account = admin_identity(authorization)
        account_id = int(account["id"])
        if admin_schedule(account_id, tournament_id) is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        proposal = dict(payload.proposal or {})
        if not proposal:
            raise HTTPException(status_code=422, detail="Importunderlaget är tomt")

        imported_matches = 0
        idempotent_replay = False
        if payload.import_matches and proposal.get("matches"):
            if not payload.fallback_date:
                raise HTTPException(
                    status_code=422,
                    detail="Cupens startdatum krävs för att importera matchtider som bara innehåller klockslag",
                )
            try:
                fallback = date.fromisoformat(str(payload.fallback_date))
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="Ogiltigt startdatum för schemaimport") from exc
            try:
                imported_matches, idempotent_replay = apply_document_matches_idempotent(
                    connect, tournament_id, proposal, fallback
                )
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

        try:
            snapshot_id = save_setup_import_snapshot(connect, tournament_id, proposal)
            location = proposal.get("location")
            if isinstance(location, str) and location.strip():
                with connect() as con:
                    con.execute(
                        "UPDATE tournaments SET arena_address=?,admin_revision=COALESCE(admin_revision,0)+1 WHERE id=? AND TRIM(COALESCE(arena_address,''))=''",
                        (location.strip(), int(tournament_id)),
                    )
                    con.commit()
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Importen kunde inte sparas för senare setupsteg") from exc
        return {
            "saved": True,
            "snapshot_id": snapshot_id,
            "imported_matches": imported_matches,
            "idempotent_replay": idempotent_replay,
            "schedule": admin_schedule(account_id, tournament_id),
        }

    @app.get("/api/admin/cups/{tournament_id}/venues")
    def get_admin_venues(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        payload = admin_venues(int(account["id"]), tournament_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.put("/api/admin/cups/{tournament_id}/venues/rules")
    def put_admin_venue_rules(
        tournament_id: int,
        payload: VenueRulesWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_venue_rules(int(account["id"]), tournament_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/venues/pitches/{pitch_number}")
    def put_admin_pitch(
        tournament_id: int,
        pitch_number: int,
        payload: PitchWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_pitch(int(account["id"]), tournament_id, pitch_number, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/venues/pitches/{pitch_number}/windows/{play_date}")
    def put_admin_pitch_window(
        tournament_id: int,
        pitch_number: int,
        play_date: str,
        payload: PitchWindowWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_pitch_window(
                int(account["id"]), tournament_id, pitch_number, play_date, _model_values(payload)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.get("/api/admin/cups/{tournament_id}/rules")
    def get_admin_rules(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        payload = admin_rules(int(account["id"]), tournament_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.put("/api/admin/cups/{tournament_id}/rules")
    def put_admin_rules(
        tournament_id: int,
        payload: CompetitionRulesWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_rules(int(account["id"]), tournament_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.get("/api/admin/cups/{tournament_id}/schedule")
    def get_admin_schedule(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        payload = admin_schedule(int(account["id"]), tournament_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.post("/api/admin/cups/{tournament_id}/schedule/confirm")
    def post_admin_schedule_confirm(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            payload = confirm_current_schedule(int(account["id"]), tournament_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.post("/api/admin/cups/{tournament_id}/schedule/proposal")
    def post_admin_schedule_proposal(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = admin_schedule_proposal(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/matchcamp/pairings/preview")
    def post_matchcamp_pairings_preview(tournament_id:int,payload:MatchcampPairingWrite,authorization:str|None=Header(default=None)):
        account=admin_identity(authorization)
        try:result=matchcamp_pairing_proposal(int(account["id"]),tournament_id,payload.matches_per_team)
        except ValueError as exc:raise HTTPException(status_code=422,detail=str(exc)) from exc
        if result is None:raise HTTPException(status_code=404,detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/matchcamp/pairings/apply")
    def post_matchcamp_pairings_apply(tournament_id:int,payload:MatchcampPairingWrite,authorization:str|None=Header(default=None)):
        account=admin_identity(authorization)
        try:result=apply_matchcamp_pairing(int(account["id"]),tournament_id,payload.matches_per_team,payload.fingerprint or "")
        except ValueError as exc:raise HTTPException(status_code=409,detail=str(exc)) from exc
        if result is None:raise HTTPException(status_code=404,detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/schedule/proposal/apply")
    def post_admin_schedule_proposal_apply(
        tournament_id: int,
        payload: ScheduleProposalApply,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = apply_schedule_proposal(int(account["id"]), tournament_id, payload.fingerprint)
        except ProposalStaleError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/schedule/matches/{match_id}")
    def put_admin_match_schedule(
        tournament_id: int,
        match_id: int,
        payload: MatchScheduleWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_match_schedule(
                int(account["id"]), tournament_id, match_id, _model_values(payload)
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Match saknas eller åtkomst nekas")
        return result

    register_competition_admin_routes(app, admin_identity)
