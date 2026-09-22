from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_owner_can_create_draft_cup_through_current_api():
    routes = (ROOT / "cupnavi_api" / "venue_admin_routes.py").read_text(encoding="utf-8")
    repository = (ROOT / "cupnavi_api" / "cup_create_repository.py").read_text(encoding="utf-8")
    assert '@app.post("/api/admin/cups", status_code=201)' in routes
    assert "create_owner_tournament" in routes
    assert "Arrangörskontot finns inte" in repository
    assert "VALUES(?,?,?,?,0,'draft')" in repository


def test_owner_ui_exposes_new_cup_and_safe_trash_flow():
    page = (ROOT / "frontend-next" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")
    shell = (ROOT / "frontend-next" / "src" / "components" / "admin-auth-shell.tsx").read_text(encoding="utf-8")
    launcher = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")
    workspace = (ROOT / "frontend-next" / "src" / "components" / "admin-workspace.tsx").read_text(encoding="utf-8")
    assert "AdminAuthShell" in page
    assert "CupCreateLauncher" in shell
    assert "Ny cup" in launcher
    assert "utkast" in launcher.lower()
    assert "Papperskorg" in workspace
    assert "Återställ" in workspace
    assert "Töm papperskorg" in workspace


def test_new_cup_switches_admin_context_to_created_cup():
    launcher = (ROOT / "frontend-next" / "src" / "components" / "cup-create-launcher-v6.tsx").read_text(encoding="utf-8")
    assert 'localStorage.setItem(CUP_KEY, String(cup.id))' in launcher
    assert 'url.searchParams.set("cup", String(cup.id))' in launcher
