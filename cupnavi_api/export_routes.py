"""FastAPI route for authenticated CupNavi PDF export."""
from __future__ import annotations

from urllib.parse import quote

from fastapi import Header, HTTPException, Response

from .export_repository import build_cup_pdf, build_public_cup_pdf


def register_export_routes(app, admin_identity):
    @app.get('/api/public/cups/{public_key}/pdf')
    def public_cup_pdf(public_key: str):
        result = build_public_cup_pdf(public_key)
        if result is None:
            raise HTTPException(status_code=404, detail='Cup not found or not published')
        return _pdf_response(result)

    @app.get('/api/admin/cups/{tournament_id}/export/pdf')
    def export_cup_pdf(tournament_id: int, authorization: str | None = Header(default=None)):
        account = admin_identity(authorization)
        result = build_cup_pdf(int(account['id']), tournament_id)
        if result is None:
            raise HTTPException(status_code=404, detail='Cup not found or access denied')
        return _pdf_response(result)


def _pdf_response(result):
    disposition = "attachment; filename*=UTF-8''" + quote(result['filename'])
    return Response(
        content=result['content'],
        media_type='application/pdf',
        headers={
            'Content-Disposition': disposition,
            'Cache-Control': 'no-store',
            'Content-Length': str(len(result['content'])),
        },
    )
