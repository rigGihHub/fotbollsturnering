from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_admin_mounts_cold_start_guard():
    page = (ROOT / "frontend-next" / "src" / "app" / "admin" / "page.tsx").read_text(encoding="utf-8")
    guard = (ROOT / "frontend-next" / "src" / "components" / "api-wake-guard.tsx").read_text(encoding="utf-8")
    assert "ApiWakeGuard" in page
    assert "CupNavi startar servern" in guard
    assert "/health" in guard
    assert "POLL_MS" in guard
    assert "window.location.reload()" in guard
    assert "Försök igen" in guard
