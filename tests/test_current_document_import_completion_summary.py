from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTES = (ROOT / "cupnavi_api" / "import_summary_routes.py").read_text(encoding="utf-8")
REPOSITORY = (ROOT / "cupnavi_api" / "import_summary_repository.py").read_text(encoding="utf-8")
COMPETITION = (ROOT / "cupnavi_api" / "competition_admin_routes.py").read_text(encoding="utf-8")
UI = (ROOT / "frontend-next" / "src" / "components" / "import-completion-summary.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend-next" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")


def test_import_summary_route_is_registered():
    assert 'register_import_summary_routes' in COMPETITION
    assert '@app.get("/api/admin/cups/{tournament_id}/import/summary")' in ROUTES


def test_import_summary_compares_snapshot_with_persisted_data():
    assert 'tournament_setup_imports' in REPOSITORY
    assert 'pitch_day_windows' in REPOSITORY
    assert 'bracket_id IS NOT NULL' in REPOSITORY
    assert '"complete": not pending' in REPOSITORY


def test_next_admin_shows_completion_summary_after_review_chain():
    assert 'ImportCompletionSummary' in PAGE
    assert 'GRANSKNINGSKEDJAN ÄR FÄRDIG' in UI
    assert 'hittades i underlaget' in UI
    assert 'publicerar aldrig cupen automatiskt' in UI
