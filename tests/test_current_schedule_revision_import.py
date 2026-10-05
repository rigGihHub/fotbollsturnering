from pathlib import Path
import sqlite3
from contextlib import contextmanager

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from cupnavi_api import schedule_revision_repository as revision, schedule_revision_routes as routes

ROOT = Path(__file__).resolve().parents[1]
REPO = (ROOT / "cupnavi_api" / "schedule_revision_repository.py").read_text(encoding="utf-8")
ROUTES = (ROOT / "cupnavi_api" / "schedule_revision_routes.py").read_text(encoding="utf-8")
COMPETITION = (ROOT / "cupnavi_api" / "competition_admin_routes.py").read_text(encoding="utf-8")
UI = (ROOT / "frontend-next" / "src" / "components" / "schedule-revision-import.tsx").read_text(encoding="utf-8")
REVIEW = (ROOT / "frontend-next" / "src" / "lib" / "schedule-revision-review.ts").read_text(encoding="utf-8")
IMPORT_UI = (ROOT / "frontend-next" / "src" / "components" / "import-admin.tsx").read_text(encoding="utf-8")


def test_revision_routes_are_registered_and_scoped_to_existing_cup():
    assert "register_schedule_revision_routes" in COMPETITION
    assert "/import/revision/analyze" in ROUTES
    assert "/schedule/revision" in ROUTES
    assert "admin_schedule(int(account[\"id\"]), tournament_id)" in ROUTES


def test_revision_commit_is_atomic_stale_safe_and_unpublishes_schedule():
    assert "expected_scheduled_start" in REPO
    assert "expected_pitch_number" in REPO
    assert "schemat har ändrats sedan granskningen" in REPO
    assert "with connect() as con:" in REPO
    assert "rollback" in REPO
    assert "schedule_dirty=1,is_published=0" in REPO


def test_revision_rejects_new_hard_conflicts():
    assert "candidate_analysis = analyze_schedule_conflicts" in REPO
    assert "Revisionen stoppades av schemakontrollen" in REPO


def test_revision_ui_requires_exact_review_before_apply():
    assert "Jämför med aktuellt schema" in UI
    assert "ingen exakt match hittades" in REVIEW
    assert "Flerdagarscuper kräver datum" in REVIEW
    assert "Genomför ${selected.length} valda ändringar" in UI
    assert "ScheduleRevisionImport" in IMPORT_UI


@pytest.fixture
def revision_db(monkeypatch, tmp_path):
    path = tmp_path / "revision.db"
    with sqlite3.connect(path) as con:
        con.executescript("""
            CREATE TABLE tournaments(id INTEGER PRIMARY KEY,is_published INTEGER,schedule_dirty INTEGER);
            CREATE TABLE matches(id INTEGER PRIMARY KEY,tournament_id INTEGER,scheduled_start TEXT,
              pitch_number INTEGER,schedule_published INTEGER,schedule_locked INTEGER,home_score INTEGER,away_score INTEGER);
            INSERT INTO tournaments VALUES(1,1,0);
            INSERT INTO matches VALUES(7,1,'2026-10-24T09:00',1,1,0,NULL,NULL);
            INSERT INTO matches VALUES(8,1,'2026-10-24T11:00',1,1,0,NULL,NULL);
        """)

    @contextmanager
    def connect():
        con = sqlite3.connect(path)
        try:
            yield con
        finally:
            con.close()

    def schedule(account_id, cup_id):
        if account_id != 1 or cup_id != 1:
            return None
        with sqlite3.connect(path) as con:
            con.row_factory = sqlite3.Row
            matches = [dict(row) for row in con.execute("SELECT * FROM matches WHERE tournament_id=1")]
        for row in matches:
            row["played"] = row["home_score"] is not None and row["away_score"] is not None
            row["home_label"], row["away_label"] = ("Örebro SK", "Bromölla") if row["id"] == 7 else ("Heming", "Premium Barcelona")
        return {"matches": matches, "start_date": "2026-10-24", "end_date": "2026-10-24", "pitch_count": 2, "pitch_names": {"1": "Sörbyvallen", "2": "Ekäng"}, "conflict_analysis": {"error_count": 0}}

    monkeypatch.setattr(revision, "connect", connect)
    monkeypatch.setattr(revision, "admin_schedule", schedule)
    monkeypatch.setattr(routes, "admin_schedule", schedule)
    monkeypatch.setattr(revision, "one", lambda *args: {})
    monkeypatch.setattr(revision, "analyze_schedule_conflicts", lambda *args: {"error_count": 0})
    return path, connect


def change(match_id=7, expected="2026-10-24T09:00"):
    return {"match_id": match_id, "scheduled_start": "2026-10-24T10:00", "pitch_number": 2,
            "expected_scheduled_start": expected, "expected_pitch_number": 1}


def test_new_pdf_is_analyzed_without_writes_then_updates_same_cup(revision_db, monkeypatch):
    path, _ = revision_db
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    extracted = {"matches": [{"home_team": "A", "away_team": "B", "time": "10:00", "venue": "Plan 2"}]}

    def extract(documents, key):
        assert documents[0][0] == b"%PDF-test"
        return dict(extracted)

    monkeypatch.setattr(routes, "extract_cup_setup_from_documents", extract)
    app = FastAPI()
    routes.register_schedule_revision_routes(app, lambda header: {"id": 1})
    client = TestClient(app)
    preview = client.post("/api/admin/cups/1/import/revision/analyze", files=[("files", ("ny.pdf", b"%PDF-test", "application/pdf"))])
    assert preview.status_code == 200
    assert preview.json()["source_name"] == "ny.pdf"
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT scheduled_start FROM matches WHERE id=7").fetchone()[0] == "2026-10-24T09:00"
        assert con.execute("SELECT is_published FROM tournaments").fetchone()[0] == 1
    committed = client.post("/api/admin/cups/1/schedule/revision", json={"changes": [change()]})
    assert committed.status_code == 200
    assert committed.json()["applied_count"] == 1
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT scheduled_start,pitch_number FROM matches WHERE id=7").fetchone() == ("2026-10-24T10:00", 2)
        assert con.execute("SELECT count(*),is_published,schedule_dirty FROM tournaments").fetchone() == (1, 0, 1)
    assert client.post("/api/admin/cups/2/schedule/revision", json={"changes": [change()]}).status_code == 404


@pytest.mark.parametrize("mutation", ["scheduled_start='2026-10-24T12:00'", "schedule_locked=1", "home_score=2,away_score=1"])
def test_revision_rolls_back_if_a_match_changes_during_saving(revision_db, monkeypatch, mutation):
    path, original_connect = revision_db

    @contextmanager
    def changed_connect():
        # Simulate another admin saving after preview checks but before the write.
        with sqlite3.connect(path) as other:
            other.execute(f"UPDATE matches SET {mutation} WHERE id=8")
        with original_connect() as con:
            yield con

    monkeypatch.setattr(revision, "connect", changed_connect)
    with pytest.raises(ValueError, match="ändrats sedan granskningen"):
        revision.apply_schedule_revision(1, 1, [change(), change(8, "2026-10-24T11:00")])
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT scheduled_start FROM matches WHERE id=7").fetchone()[0] == "2026-10-24T09:00"
        assert con.execute("SELECT is_published FROM tournaments").fetchone()[0] == 1


def test_real_pdf_fallback_after_ai_outage_then_persists_every_reviewed_change(revision_db, monkeypatch):
    from io import BytesIO
    from reportlab.pdfgen.canvas import Canvas

    path, _ = revision_db
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    def unavailable(*args):
        raise RuntimeError("AI-tjänsten är tillfälligt otillgänglig")

    monkeypatch.setattr(routes, "extract_cup_setup_from_documents", unavailable)
    raw = BytesIO()
    pdf = Canvas(raw)
    pdf.drawString(40, 760, "Slottskampen - uppdaterat spelschema")
    pdf.drawString(40, 730, "09:45 Ekäng Örebro SK - Bromölla")
    pdf.drawString(40, 700, "11:45 Sörbyvallen Heming - PremiumBarcelona")
    pdf.save()
    app = FastAPI()
    routes.register_schedule_revision_routes(app, lambda header: {"id": 1})
    client = TestClient(app)
    preview = client.post("/api/admin/cups/1/import/revision/analyze", files=[("files", ("ny.pdf", raw.getvalue(), "application/pdf"))])
    assert preview.status_code == 200
    proposal = preview.json()
    assert proposal["extraction_method"] == "pdf_text"
    assert [row["time"] for row in proposal["matches"]] == ["09:45", "11:45"]
    assert proposal["matches"][1]["away_team"] == "Premium Barcelona"
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT scheduled_start FROM matches WHERE id=7").fetchone()[0] == "2026-10-24T09:00"
    commits = [dict(change(), scheduled_start="2026-10-24T09:45"),
               dict(change(8, "2026-10-24T11:00"), scheduled_start="2026-10-24T11:45", pitch_number=1)]
    saved = client.post("/api/admin/cups/1/schedule/revision", json={"changes": commits})
    assert saved.status_code == 200
    assert saved.json()["applied_count"] == 2
    assert [row["scheduled_start"] for row in saved.json()["schedule"]["matches"]] == ["2026-10-24T09:45", "2026-10-24T11:45"]
    with sqlite3.connect(path) as con:
        assert con.execute("SELECT id,scheduled_start,pitch_number FROM matches ORDER BY id").fetchall() == [
            (7, "2026-10-24T09:45", 2), (8, "2026-10-24T11:45", 1)]


def test_pdf_without_readable_rows_reports_outage_instead_of_empty_success(revision_db, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(routes, "extract_cup_setup_from_documents", lambda *args: (_ for _ in ()).throw(RuntimeError("AI-tjänsten är tillfälligt otillgänglig")))
    app = FastAPI()
    routes.register_schedule_revision_routes(app, lambda header: {"id": 1})
    response = TestClient(app).post("/api/admin/cups/1/import/revision/analyze", files=[("files", ("bild.png", b"image-fixture", "image/png"))])
    assert response.status_code == 502
    assert "tillfälligt otillgänglig" in response.json()["detail"]


def test_text_fallback_requires_explicit_pair_and_unique_venue():
    from cupnavi_core.schedule_revision_text import extract_schedule_revision_text
    schedule = {"matches": [{"home_label": "Örebro SK", "away_label": "Bromölla"}], "pitch_names": {"1": "Ekäng", "2": "Sörbyvallen"}}
    parse = lambda text: extract_schedule_revision_text([(text.encode(), "schema.txt", "text/plain")], schedule)
    assert parse("09:30 Ekäng Örebro SK Bromölla") is None  # Roster, no match separator.
    assert parse("09:30 Ekäng Sörbyvallen Örebro SK - Bromölla") is None
    partial = parse("09:30 Ekäng Örebro SK - Bromölla\n10:30 Okänd plan Örebro SK - Bromölla")
    assert len(partial["matches"]) == 1 and len(partial["unread_rows"]) == 1
    assert parse("2026-10-25T09:30 Ekäng Örebro SK - Bromölla")["matches"][0]["time"] == "2026-10-25T09:30"


def test_ai_retries_temporary_503_but_not_bad_requests():
    from io import BytesIO
    from urllib.error import HTTPError
    from urllib.request import Request
    from cupnavi_core.ai_cup_document_import import _request_payload

    attempts, pauses = [], []

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self): return b'{"output": []}'

    def recovered(request, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            raise HTTPError(request.full_url, 503, "unavailable", {}, BytesIO(b"upstream connection refused"))
        return Response()

    request = Request("https://api.openai.com/v1/responses")
    assert _request_payload(request, 90, recovered, pause=pauses.append)["output"] == []
    assert len(attempts) == 2 and pauses == [1]
    for status in [400, 503]:
        attempts.clear(); pauses.clear()

        def failed(request, **kwargs):
            attempts.append(1)
            raise HTTPError(request.full_url, status, "failed", {}, BytesIO(b"upstream connection refused"))

        with pytest.raises(RuntimeError) as error:
            _request_payload(request, 90, failed, pause=pauses.append)
        assert len(attempts) == (1 if status == 400 else 3)
        if status == 503:
            assert "upstream" not in str(error.value)


def test_pdf_table_cells_and_last_placement_row_are_not_lost_to_footer():
    from cupnavi_core.schedule_revision_text import extract_schedule_revision_text
    text='''TID PLAN GRP HEMMA BORTA RESULTAT
13:45 Sörbyvallen B
Heming
AIK –
GRUPP A OCH C FÖRST KLARA
Grupp B slutar 14:23 och kliver in först 16:05.
SLUTSPEL
TID PLAN SERIE MATCH TID/H RESULTAT
17:50 Sörbyvallen GULDGRUPPEN 1:a grupp A – 1:a grupp B 2×20 –
SÅ AVGÖRS PLACERINGARNA
'''+'fotnot '*150+'\n17:50 även silvergruppens sista match.'
    proposal=extract_schedule_revision_text([(text.encode(),'schema.txt','text/plain')],{'matches':[{'home_label':'Heming','away_label':'AIK'}],'pitch_names':{'1':'Sörbyvallen'}})
    assert len(proposal['matches'])==1 and proposal['matches'][0]['group_name']=='B'
    assert len(proposal['playoff_matches'])==1
    assert proposal['playoff_matches'][0]['away_source']=='1:a grupp B'
    assert proposal['unread_rows']==[]
