from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = (ROOT / "cupnavi_api" / "playoff_import_repository.py").read_text(encoding="utf-8")
ROUTES = (ROOT / "cupnavi_api" / "playoff_import_routes.py").read_text(encoding="utf-8")
COMPETITION = (ROOT / "cupnavi_api" / "competition_admin_routes.py").read_text(encoding="utf-8")
UI = (ROOT / "frontend-next" / "src" / "components" / "playoff-import-review.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend-next" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")


def test_reviewed_playoff_import_routes_are_registered():
    assert 'register_playoff_import_routes' in COMPETITION
    assert '@app.get("/api/admin/cups/{tournament_id}/import/playoffs")' in ROUTES
    assert '@app.post("/api/admin/cups/{tournament_id}/import/playoffs")' in ROUTES


def test_playoff_import_never_silently_replaces_existing_tree():
    assert "Cupen har redan ett slutspelsträd" in REPOSITORY
    assert "rollback" in REPOSITORY
    assert "validate_bracket_sources" in REPOSITORY


def test_playoff_import_uses_canonical_participant_sources():
    assert 'f"team:{team_id}"' in REPOSITORY
    assert 'f"group:{group_id}:{int(group_match.group(1))}"' in REPOSITORY
    assert 'f"{kind}:{dependency}"' in REPOSITORY
    assert "Olösbara slutspelskällor" in REPOSITORY


def test_next_admin_exposes_review_first_playoff_flow():
    assert "PlayoffImportReview" in PAGE
    assert "Slutspel väntar på granskning" in UI
    assert "Granska slutspel" in UI
    assert "Importera granskat slutspel" in UI
    assert "Befintligt slutspel skrivs aldrig över" in UI
