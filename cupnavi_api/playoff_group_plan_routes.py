from fastapi import Header, HTTPException
from pydantic import BaseModel
from .playoff_group_plan_repository import preview_group_playoffs, apply_group_playoffs, restore_previous_playoffs
from .playoff_admin_repository import admin_playoffs


class GroupPlayoffPlanWrite(BaseModel):
    revision: str | None = None
    source_rows: list[dict] | None = None
    source_name: str | None = None


def register_playoff_group_plan_routes(app, admin_identity):
    def call(function, account_id, tournament_id, *args):
        try:
            result = function(account_id, tournament_id, *args)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        if result is None:
            raise HTTPException(404, "Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/playoffs/group-plan/preview")
    def preview(tournament_id: int, payload: GroupPlayoffPlanWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        return call(preview_group_playoffs, int(account["id"]), tournament_id, payload.source_rows, payload.source_name)

    @app.post("/api/admin/cups/{tournament_id}/playoffs/group-plan/apply")
    def apply(tournament_id: int, payload: GroupPlayoffPlanWrite, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        if not payload.revision:
            raise HTTPException(422, "Förhandsgranska slutspelet innan du genomför bytet")
        call(apply_group_playoffs, int(account["id"]), tournament_id, payload.revision, payload.source_rows, payload.source_name)
        return admin_playoffs(int(account["id"]), tournament_id)

    @app.post("/api/admin/cups/{tournament_id}/playoffs/group-plan/restore")
    def restore(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        call(restore_previous_playoffs, int(account["id"]), tournament_id)
        return admin_playoffs(int(account["id"]), tournament_id)
