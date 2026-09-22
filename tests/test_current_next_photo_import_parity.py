from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")
STEPS = (ROOT / "frontend-next" / "src" / "components" / "cup-import-steps.ts").read_text(encoding="utf-8")
ROUTES = (ROOT / "cupnavi_api" / "venue_admin_routes.py").read_text(encoding="utf-8")


def test_next_new_cup_offers_manual_or_photo_pdf_import():
    assert "Skapa manuellt" in LAUNCHER
    assert "Bild eller PDF" in LAUNCHER
    assert 'type="file"' in LAUNCHER
    assert 'multiple' in LAUNCHER
    assert ".pdf,.txt,.png,.jpg,.jpeg,.webp" in LAUNCHER


def test_next_photo_import_is_review_first():
    assert "sparar inget förrän du" in LAUNCHER
    assert "Redo att skapa" in LAUNCHER
    assert "Lag & grupper" in LAUNCHER
    assert "Behöver åtgärdas" in LAUNCHER


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


def test_reviewed_schedule_can_be_persisted_but_playoffs_are_still_deferred():
    assert "/import/initial`" in LAUNCHER
    assert "import_matches" in LAUNCHER
    assert "fallback_date" in LAUNCHER
    assert "playoff_matches" in LAUNCHER
    assert 'goToCup(cup,playoffMatches.length?"playoffs":"overview")' in LAUNCHER


def test_photo_import_reviews_detected_playoff_before_final_control():
    assert '{ id: 3, label: "Slutspel" }' in STEPS
    assert "<h3>Slutspel</h3>" in LAUNCHER
    assert "slutspelsmatcher · sparas för separat granskning" in LAUNCHER
    assert "updatePlayoffMatch" in LAUNCHER


def test_photo_import_deduplicates_teams_before_saving():
    assert "uniqueImportedTeams" in LAUNCHER
    assert "dubblettrad med lag slogs ihop" in LAUNCHER
    assert "redan ett lag med samma namn" in LAUNCHER
