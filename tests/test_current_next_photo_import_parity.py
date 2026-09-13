from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher.tsx").read_text(encoding="utf-8")
ROUTES = (ROOT / "cupnavi_api" / "venue_admin_routes.py").read_text(encoding="utf-8")


def test_next_new_cup_offers_manual_or_photo_pdf_import():
    assert "Skapa manuellt" in LAUNCHER
    assert "Importera bild / PDF" in LAUNCHER
    assert 'type="file" multiple' in LAUNCHER
    assert ".pdf,.txt,.png,.jpg,.jpeg,.webp" in LAUNCHER


def test_next_photo_import_is_review_first():
    assert "sparar inget förrän du har granskat resultatet" in LAUNCHER
    assert "Skapa cup från granskningen" in LAUNCHER
    assert "Lag som kommer importeras" in LAUNCHER
    assert "Kontrollera innan du fortsätter" in LAUNCHER


def test_next_photo_import_reuses_existing_ai_extractor():
    assert "extract_cup_setup_from_documents" in ROUTES
    assert '@app.post("/api/admin/cup-import/analyze")' in ROUTES
    assert 'os.getenv("OPENAI_API_KEY"' in ROUTES


def test_reviewed_import_restores_core_setup_data():
    assert '/groups`' in LAUNCHER
    assert '/teams`' in LAUNCHER
    assert '/venues/rules`' in LAUNCHER
    assert '/rules`' in LAUNCHER
    assert "group_id" in LAUNCHER


def test_schedule_and_playoffs_are_not_silently_written_yet():
    assert "själva matchschemat förs in i nästa återställningsblock" in LAUNCHER
    assert "Slutspelsimport kopplas in i nästa block" in LAUNCHER
