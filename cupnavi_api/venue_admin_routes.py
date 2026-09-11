"""FastAPI route registration for organizer pitch and availability administration."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

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
            result = update_venue_rules(
                int(account["id"]), tournament_id, _model_values(payload)
            )
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
            result = update_pitch(
                int(account["id"]), tournament_id, pitch_number, _model_values(payload)
            )
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
                int(account["id"]),
                tournament_id,
                pitch_number,
                play_date,
                _model_values(payload),
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
