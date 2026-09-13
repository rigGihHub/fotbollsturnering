from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = (ROOT / "cupnavi_api" / "schedule_revision_repository.py").read_text(encoding="utf-8")
ROUTES = (ROOT / "cupnavi_api" / "schedule_revision_routes.py").read_text(encoding="utf-8")
COMPETITION = (ROOT / "cupnavi_api" / "competition_admin_routes.py").read_text(encoding="utf-8")
UI = (ROOT / "frontend-next" / "src" / "components" / "schedule-revision-import.tsx").read_text(encoding="utf-8")
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
    assert "ingen exakt match hittades" in UI
    assert "Flerdagarscuper kräver datum" in UI
    assert "Applicera ${selected.length} valda ändringar" in UI
    assert "ScheduleRevisionImport" in IMPORT_UI
