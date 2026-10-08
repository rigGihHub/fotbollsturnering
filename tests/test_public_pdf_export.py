from io import BytesIO
import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfReader

from cupnavi_api import export_repository, export_routes


@pytest.fixture
def public_export_db(tmp_path, monkeypatch):
    database = tmp_path / "export.db"
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    monkeypatch.setenv("CUPNAVI_API_SQLITE_PATH", str(database))
    with sqlite3.connect(database) as con:
        con.executescript("""
            CREATE TABLE tournaments (id INTEGER PRIMARY KEY, name TEXT, public_slug TEXT,
                is_published INTEGER, lifecycle_status TEXT);
            CREATE TABLE groups (id INTEGER, tournament_id INTEGER, name TEXT, age_class TEXT);
            CREATE TABLE teams (id INTEGER, tournament_id INTEGER, name TEXT, group_id INTEGER, age_class TEXT);
            CREATE TABLE pitches (tournament_id INTEGER, pitch_number INTEGER, name TEXT);
            CREATE TABLE matches (id INTEGER, tournament_id INTEGER, scheduled_start TEXT,
                schedule_published INTEGER, home_source TEXT, away_source TEXT);
            INSERT INTO tournaments VALUES (42,'Slottskampen','slottskampen-6',1,'active');
            INSERT INTO tournaments VALUES (43,'Utkast','draft',0,'draft');
            INSERT INTO tournaments VALUES (44,'Borttagen','trashed',1,'trashed');
            INSERT INTO tournaments VALUES (45,'Raderad','purged',1,'purged');
            INSERT INTO teams VALUES (1,42,'Örebro SK',NULL,NULL),(2,42,'Bromölla',NULL,NULL);
            INSERT INTO matches VALUES (1,42,'2026-10-24T08:30',1,'team:1','team:2');
            INSERT INTO matches VALUES (2,42,'2026-10-24T09:30',0,'DOLD MATCH','team:2');
            INSERT INTO matches VALUES (3,42,NULL,1,'UTAN TID','team:2');
        """)
    return database


@pytest.mark.parametrize("public_key", ["42", "slottskampen-6"])
def test_public_pdf_route_supports_same_keys_as_cup_page(public_export_db, public_key):
    app = FastAPI()
    export_routes.register_export_routes(app, lambda authorization: {"id": 1})
    response = TestClient(app).get(f"/api/public/cups/{public_key}/pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "slottskampen-6.pdf" in response.headers["content-disposition"]
    reader = PdfReader(BytesIO(response.content))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Slottskampen" in text and "Örebro SK" in text and "Bromölla" in text
    assert "DOLD MATCH" not in text and "UTAN TID" not in text
    tournament = {"id": 42, "name": "Slottskampen"}
    assert len(export_repository._snapshot_for_tournament(tournament)["matches"]) == 3


@pytest.mark.parametrize("public_key", ["43", "draft", "44", "trashed", "45", "purged", "999"])
def test_public_pdf_rejects_private_or_removed_cups_by_slug_and_id(public_export_db, public_key):
    assert export_repository.build_public_cup_pdf(public_key) is None


def test_public_pdf_prefers_exact_slug_over_numeric_id(public_export_db):
    with sqlite3.connect(public_export_db) as con:
        con.execute("INSERT INTO tournaments VALUES (46,'Numerisk slug','42',1,'active')")
    assert export_repository.public_export_snapshot("42")["tournament"]["id"] == 46


def test_public_pdf_contains_current_cup_and_requires_publication(monkeypatch):
    def tournament(sql, params):
        assert "(public_slug=? OR id=?) AND is_published=1" in sql
        assert "lifecycle_status" in sql
        return {"id": 42, "name": "Slottskampen", "public_slug": "slottskampen-6"} if params == ("slottskampen-6", -1, "slottskampen-6") else None

    def rows(sql, params):
        assert params == (42,)
        if "FROM groups" in sql:
            return [{"id": 54, "name": "C", "age_class": None}]
        if "FROM teams" in sql:
            return [{"id": 1, "name": "Örebro SK", "group_id": None}]
        if "FROM matches" in sql:
            assert "schedule_published=1 AND scheduled_start IS NOT NULL" in sql
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
