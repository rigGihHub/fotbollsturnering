from io import BytesIO
from pathlib import Path

from pypdf import PdfReader
from cupnavi_core.pdf_export import build_schedule_pdf


def sample_pdf():
    tournament = {
        "name": "Testcupen",
        "location": "Örebro",
        "tournament_date": "2026-08-21",
        "start_date": "2026-08-21",
        "end_date": "2026-08-22",
    }
    teams = [
        {"id": 1, "name": "Lag A", "group_id": 10},
        {"id": 2, "name": "Lag B", "group_id": 10},
    ]
    groups = [{"id": 10, "name": "Grupp A"}]
    referees = [{"id": 5, "name": "Domare Ett"}]
    matches = [{
        "id": 100, "group_id": 10, "stage": "Gruppspel",
        "scheduled_start": "2026-08-21T09:00", "pitch_number": 1,
        "home_source": "team:1", "away_source": "team:2",
        "home_score": None, "away_score": None,
        "home_penalties": None, "away_penalties": None,
        "referee_id": 5,
    }]
    labels = {"team:1": "Lag A", "team:2": "Lag B"}
    ids = {"team:1": 1, "team:2": 2}
    return build_schedule_pdf(tournament, matches, teams, groups, referees, labels, ids)


def test_pdf_export_is_valid_pdf():
    data = sample_pdf()
    assert data.startswith(b"%PDF")
    reader = PdfReader(BytesIO(data))
    assert len(reader.pages) >= 2


def test_pdf_export_contains_expected_sections():
    data = sample_pdf()
    reader = PdfReader(BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "Hela spelschemat" in text
    assert "Gruppscheman" in text
    assert "Lagscheman" in text
    assert "Planscheman" in text
    assert "Domarschema" in text


def test_app_exposes_pdf_download():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "Skapa komplett schemapaket som PDF" in text
    assert "Ladda ner alla scheman som PDF" in text
    assert 'mime="application/pdf"' in text


def test_reportlab_is_required():
    requirements = Path("requirements.txt").read_text(encoding="utf-8")
    assert "reportlab" in requirements
