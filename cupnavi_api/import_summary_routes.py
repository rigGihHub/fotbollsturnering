"""Authenticated summary route for the review-first document import chain."""
from __future__ import annotations

from fastapi import Header, HTTPException

from .import_summary_repository import import_summary


def register_import_summary_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/import/summary")
    def get_import_summary(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = import_summary(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
