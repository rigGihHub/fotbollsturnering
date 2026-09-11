"""FastAPI route registration for organizer competition rules."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .rules_admin_repository import admin_rules, update_rules


class RulesWrite(BaseModel):
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


def _model_values(model: BaseModel) -> dict:
    model_dump = getattr(model, "model_dump", None)
    return model_dump(exclude_unset=True) if callable(model_dump) else model.dict(exclude_unset=True)


def register_rules_admin_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/rules")
    def get_admin_rules(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = admin_rules(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.put("/api/admin/cups/{tournament_id}/rules")
    def put_admin_rules(
        tournament_id: int,
        payload: RulesWrite,
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
