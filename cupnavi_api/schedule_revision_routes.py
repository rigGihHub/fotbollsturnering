"""Routes for review-first schedule revisions extracted from photos/documents."""
from __future__ import annotations

import os

from fastapi import File, Header, HTTPException, UploadFile
from pydantic import BaseModel

from cupnavi_core.ai_cup_document_import import extract_cup_setup_from_documents

from .schedule_admin_repository import admin_schedule
from .schedule_revision_repository import apply_schedule_revision


class ScheduleRevisionRow(BaseModel):
    match_id: int
    scheduled_start: str
    pitch_number: int
    expected_scheduled_start: str | None = None
    expected_pitch_number: int | None = None


class ScheduleRevisionCommit(BaseModel):
    changes: list[ScheduleRevisionRow]


def _values(model: BaseModel) -> dict:
    dump = getattr(model, "model_dump", None)
    return dump() if callable(dump) else model.dict()


def register_schedule_revision_routes(app, admin_identity):
    @app.post("/api/admin/cups/{tournament_id}/import/revision/analyze")
    async def analyze_schedule_revision(
        tournament_id: int,
        files: list[UploadFile] = File(...),
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        if admin_schedule(int(account["id"]), tournament_id) is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        if not files:
            raise HTTPException(status_code=422, detail="Välj minst en bild eller PDF")
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise HTTPException(status_code=503, detail="AI-importen är inte konfigurerad på servern")
        documents = []
        for upload in files:
            raw = await upload.read()
            documents.append((raw, upload.filename or "revision", upload.content_type or ""))
        try:
            extracted = extract_cup_setup_from_documents(documents, api_key)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        extracted["source_name"] = ", ".join(upload.filename or "revision" for upload in files)
        return extracted

    @app.post("/api/admin/cups/{tournament_id}/schedule/revision")
    def commit_schedule_revision(
        tournament_id: int,
        payload: ScheduleRevisionCommit,
        authorization: str | None = Header(default=None),
    ):
        account = admin_identity(authorization)
        try:
            result = apply_schedule_revision(
                int(account["id"]), tournament_id, [_values(row) for row in payload.changes]
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        if result is None:
            raise HTTPException(status_code=404, detail="Cup not found or access denied")
        return result
