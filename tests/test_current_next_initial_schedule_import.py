from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "cupnavi_api" / "venue_admin_routes.py").read_text(encoding="utf-8")
LAUNCHER = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")


def test_initial_import_snapshot_is_persisted_in_next_flow():
    assert 'save_setup_import_snapshot' in ROUTES
    assert '@app.post("/api/admin/cups/{tournament_id}/import/initial")' in ROUTES
    assert 'snapshot_id' in ROUTES
    assert 'proposal,' in LAUNCHER
    assert 'import_matches: importSchedule && matches.length > 0' in LAUNCHER


def test_reviewed_group_schedule_can_follow_first_import():
    assert 'apply_document_matches' in ROUTES
    assert 'fallback_date' in ROUTES
    assert 'Importera det granskade schemat' in LAUNCHER
    assert '<h3>Matcher</h3>' in LAUNCHER
    assert 'fallback_date' in LAUNCHER


def test_next_schedule_import_keeps_review_first_guards():
    assert 'Import sparar inget förrän du' in LAUNCHER
    assert 'Blockerar skapande' in LAUNCHER
    assert 'schedule_locked' in (ROOT / "cupnavi_core" / "cup_document_creator_view.py").read_text(encoding="utf-8")
