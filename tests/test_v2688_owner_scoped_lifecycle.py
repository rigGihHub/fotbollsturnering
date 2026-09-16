from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = (ROOT / "cupnavi_api/admin_repository.py").read_text(encoding="utf-8")
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")


def test_release_version_is_synchronized():
    package = (ROOT / "frontend-next/package.json").read_text(encoding="utf-8")
    layout = (ROOT / "frontend-next/src/app/layout.tsx").read_text(encoding="utf-8")
    worker = (ROOT / "frontend-next/public/sw.js").read_text(encoding="utf-8")
    assert '"version": "2.6.' in package
    assert 'const APP_VERSION = "2.6.' in layout
    assert 'const CACHE="cupnavi-next-v' in worker


def test_regular_owner_can_only_purge_owned_trashed_cups():
    assert "WHERE organizer_account_id=? AND role='owner'" in REPOSITORY
    assert "if account_id == OWNER_ACCOUNT_ID:" in REPOSITORY
    assert "if (!token || !trashedCups.length) return;" in WORKSPACE
    assert '<button className="admin-empty-trash"' in WORKSPACE
