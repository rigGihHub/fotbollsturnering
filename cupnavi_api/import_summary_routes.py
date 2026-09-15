"""Authenticated summary route for the review-first document import chain."""
from __future__ import annotations

from fastapi import Header, HTTPException

from .import_summary_repository import import_summary, restore_initial_matches


def register_import_summary_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/import/summary")
    def get_import_summary(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = import_summary(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/import/restore-matches")
    def post_restore_initial_matches(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        try:
            result = restore_initial_matches(int(account["id"]), tournament_id)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
