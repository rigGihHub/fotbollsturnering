"""Routes for review-first pitch-window import from the saved initial document scan."""
from __future__ import annotations

from fastapi import Header, HTTPException
from pydantic import BaseModel

from .pitch_window_import_repository import commit_pitch_window_import, pitch_window_import_review


class PitchWindowImportRow(BaseModel):
    venue: str | None = None
    date: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class PitchWindowImportCommit(BaseModel):
    pitch_windows: list[PitchWindowImportRow]


def _model_values(model: BaseModel) -> dict:
    dump = getattr(model, "model_dump", None)
    return dump() if callable(dump) else model.dict()


def register_pitch_window_import_routes(app, admin_identity):
    @app.get("/api/admin/cups/{tournament_id}/import/pitch-windows")
    def get_pitch_window_import_review(
        tournament_id: int,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        result = pitch_window_import_review(int(account["id"]), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result

    @app.post("/api/admin/cups/{tournament_id}/import/pitch-windows")
    def post_pitch_window_import(
        tournament_id: int,
        payload: PitchWindowImportCommit,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        rows = [_model_values(row) for row in payload.pitch_windows]
        try:
            result = commit_pitch_window_import(int(account["id"]), tournament_id, rows)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
