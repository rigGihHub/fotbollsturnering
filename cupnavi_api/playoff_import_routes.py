"""Routes for reviewing and committing playoff rows found in the initial document import."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .playoff_import_repository import commit_playoff_import, playoff_import_review


class PlayoffImportWrite(BaseModel):
    playoff_matches: list[dict]
    playoff_rule_values: dict | None = None


def register_playoff_import_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/import/playoffs")
    def get_playoff_import(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = playoff_import_review(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/import/playoffs")
    def post_playoff_import(
        tournament_id: int,
        payload: PlayoffImportWrite,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = commit_playoff_import(
                int(account["id"]),
                tournament_id,
                payload.playoff_matches,
                payload.playoff_rule_values,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
