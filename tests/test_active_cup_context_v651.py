from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")


def test_active_cup_context_prefers_only_an_authorized_url_or_stored_id():
    assert 'const CUP_KEY = "cupnavi_admin_active_cup_v651"' in WORKSPACE
    assert 'cups.find(cup => cup.id === requested)' in WORKSPACE
    assert 'cups.find(cup => cup.id === stored)' in WORKSPACE
    assert 'if (!cups.some(cup => cup.id === nextId))' in WORKSPACE


def test_active_cup_context_survives_reload_and_supports_deep_links():
    assert 'localStorage.setItem(CUP_KEY,String(cupId))' in WORKSPACE
    assert 'url.searchParams.set("cup",String(cupId))' in WORKSPACE
    assert 'window.history.replaceState' in WORKSPACE
    assert WORKSPACE.count("rememberCup(selected.id)") == 2


def test_owner_access_copy_does_not_claim_membership_scoping():
    assert 'account.role === "owner" || account.is_owner === true' in WORKSPACE
    assert "har åtkomst till alla cuper" in WORKSPACE
    assert 'isOwner ? "ägare"' in WORKSPACE


def test_v651_release_is_synchronized():
    version = "2026.09.12-651-ACTIVE-CUP-CONTEXT"
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == version
    assert f'APP_VERSION = "{version}"' in (ROOT / "cupnavi_core/version.py").read_text(encoding="utf-8")
