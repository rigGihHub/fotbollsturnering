"""Authenticated team import routes."""
from __future__ import annotations

from fastapi import File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from .import_repository import commit_team_import, preview_team_import


class ImportTeamRow(BaseModel):
    name: str
    age_class: str | None = None
    group_id: int | None = None
    primary_color: str | None = None
    secondary_color: str | None = None


class ImportCommit(BaseModel):
    rows: list[ImportTeamRow]


def _values(model):
    dump = getattr(model, "model_dump", None)
    return dump() if callable(dump) else model.dict()


def register_import_routes(app, admin_identity):
    @app.post('/api/admin/cups/{tournament_id}/import/teams/preview')
    async def preview_import(
        tournament_id: int,
        file: UploadFile = File(...),
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        filename = file.filename or "import"
        content = await file.read()
        try:
            result = preview_team_import(int(account['id']), tournament_id, content, filename)
        except (ValueError, UnicodeDecodeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail='Cup not found or access denied')
        return result

    @app.post('/api/admin/cups/{tournament_id}/import/teams/commit')
    def commit_import(
        tournament_id: int,
        payload: ImportCommit,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = commit_team_import(int(account['id']), tournament_id, [_values(row) for row in payload.rows])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail='Cup not found or access denied')
        return result
