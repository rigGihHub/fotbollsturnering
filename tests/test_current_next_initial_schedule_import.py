from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "cupnavi_api" / "venue_admin_routes.py").read_text(encoding="utf-8")
LAUNCHER = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher.tsx").read_text(encoding="utf-8")


def test_initial_import_snapshot_is_persisted_in_next_flow():
    assert 'save_setup_import_snapshot' in ROUTES
    assert '@app.post("/api/admin/cups/{tournament_id}/import/initial")' in ROUTES
    assert 'snapshot_id' in ROUTES
    assert 'proposal,import_matches:importSchedule' in LAUNCHER


def test_reviewed_group_schedule_can_follow_first_import():
    assert 'apply_document_matches' in ROUTES
    assert 'fallback_date' in ROUTES
    assert 'Använd det granskade matchprogrammet som cupens befintliga schema' in LAUNCHER
    assert 'Granska matchschema' in LAUNCHER
    assert 'CupNavi gissar inte vilket datum ett klockslag hör till' in LAUNCHER


def test_next_schedule_import_keeps_review_first_guards():
    assert 'Foto/PDF-import sparar inget förrän du har granskat resultatet.' in LAUNCHER
    assert 'Importen stoppas om ett lag, en grupp eller plan inte stämmer' in LAUNCHER
    assert 'schedule_locked' in (ROOT / "cupnavi_core" / "cup_document_creator_view.py").read_text(encoding="utf-8")
