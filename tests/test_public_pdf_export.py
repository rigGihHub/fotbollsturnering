from io import BytesIO

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from cupnavi_api import export_repository, export_routes


def test_public_pdf_contains_current_cup_and_requires_published_slug(monkeypatch):
    def tournament(sql, params):
        assert "public_slug=? AND is_published=1" in sql
        assert "lifecycle_status" in sql
        return {"id": 42, "name": "Slottskampen", "public_slug": "slottskampen-6"} if params == ("slottskampen-6",) else None

    def rows(sql, params):
        assert params == (42,)
        if "FROM groups" in sql:
            return [{"id": 54, "name": "C", "age_class": None}]
        if "FROM teams" in sql:
            return [{"id": 1, "name": "Örebro SK", "group_id": None}]
        if "FROM matches" in sql:
            return [{"home_source": "team:1", "away_source": "group:54:2", "scheduled_start": "2026-10-24T08:30", "pitch_number": 1}]
        return []

    monkeypatch.setattr(export_repository, "one", tournament)
    monkeypatch.setattr(export_repository, "all_rows", rows)

    assert export_repository.build_public_cup_pdf("draft") is None
    pdf = export_repository.build_public_cup_pdf("slottskampen-6")
    assert pdf["filename"] == "slottskampen-6.pdf"
    assert pdf["content"].startswith(b"%PDF-")
    pages = PdfReader(BytesIO(pdf["content"])).pages
    text = "\n".join(page.extract_text() or "" for page in pages)
    assert "Slottskampen" in text
    assert "24/10 08:30" in text
    assert "team:1" not in text
    assert "group:54:2" not in text


def test_public_pdf_route_rejects_unpublished_cup(monkeypatch):
    app = FastAPI()
    export_routes.register_export_routes(app, lambda authorization: {"id": 1})
    monkeypatch.setattr(export_routes, "build_public_cup_pdf", lambda key: None)
    response = TestClient(app).get("/api/public/cups/draft/pdf")
    assert response.status_code == 404
