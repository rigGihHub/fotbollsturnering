"""FastAPI route registration for organizer setup and schedule administration."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .competition_admin_routes import register_competition_admin_routes
from .rules_admin_repository import admin_rules, update_rules
from .schedule_admin_repository import admin_schedule, update_match_schedule
from .schedule_proposal_repository import ProposalStaleError, admin_schedule_proposal, apply_schedule_proposal
from .venue_admin_repository import (
    admin_venues,
    update_pitch,
    update_pitch_window,
    update_venue_rules,
)


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


def _model_values(model: BaseModel) -> dict:
    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def register_venue_admin_routes(app, admin_identity):
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

    @app.post("/api/admin/cups/{tournament_id}/schedule/proposal")
    def post_admin_schedule_proposal(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = admin_schedule_proposal(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
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
