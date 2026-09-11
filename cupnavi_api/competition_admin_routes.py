"""FastAPI route registration for referee and playoff administration."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .playoff_admin_repository import admin_playoffs, update_playoff_settings
from .referee_admin_repository import (
    admin_referees,
    assign_referee,
    create_referee,
    delete_referee,
    update_referee,
)


class RefereeWrite(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    notes: str | None = None
    active: bool | None = None


class RefereeAssignmentWrite(BaseModel):
    referee_id: int | None = None


class PlayoffSettingsWrite(BaseModel):
    playoff_format: str | None = None
    bronze_match: bool | None = None
    playoff_tie_rule: str | None = None
    playoff_extra_time_minutes: int | None = None


def _model_values(model: BaseModel) -> dict:
    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        return model_dump(exclude_unset=True)
    return model.dict(exclude_unset=True)


def register_competition_admin_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/referees")
    def get_admin_referees(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        payload = admin_referees(int(account["id"]), tournament_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.post("/api/admin/cups/{tournament_id}/referees", status_code=201)
    def post_admin_referee(
        tournament_id: int,
        payload: RefereeWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = create_referee(int(account["id"]), tournament_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/referees/{referee_id}")
    def put_admin_referee(
        tournament_id: int,
        referee_id: int,
        payload: RefereeWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_referee(int(account["id"]), tournament_id, referee_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Domare saknas eller åtkomst nekas")
        return result

    @app.delete("/api/admin/cups/{tournament_id}/referees/{referee_id}")
    def remove_admin_referee(
        tournament_id: int,
        referee_id: int,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = delete_referee(int(account["id"]), tournament_id, referee_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Domare saknas eller åtkomst nekas")
        return {"deleted": True, "referee": result}

    @app.put("/api/admin/cups/{tournament_id}/referees/matches/{match_id}")
    def put_admin_referee_assignment(
        tournament_id: int,
        match_id: int,
        payload: RefereeAssignmentWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = assign_referee(int(account["id"]), tournament_id, match_id, payload.referee_id)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Match saknas eller åtkomst nekas")
        return result

    @app.get("/api/admin/cups/{tournament_id}/playoffs")
    def get_admin_playoffs(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        payload = admin_playoffs(int(account["id"]), tournament_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return payload

    @app.put("/api/admin/cups/{tournament_id}/playoffs")
    def put_admin_playoffs(
        tournament_id: int,
        payload: PlayoffSettingsWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = update_playoff_settings(int(account["id"]), tournament_id, _model_values(payload))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
