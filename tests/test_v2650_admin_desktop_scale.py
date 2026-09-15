from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CSS = (ROOT / "frontend-next/src/app/admin-desktop-v2650.css").read_text(encoding="utf-8")
LAYOUT = (ROOT / "frontend-next/src/app/admin/layout.tsx").read_text(encoding="utf-8")


def test_desktop_workspace_uses_available_screen_width():
    assert "@media (min-width: 1000px)" in CSS
    assert "width: min(1500px, calc(100% - 48px))" in CSS
    assert "grid-template-columns: 280px minmax(0, 1fr)" in CSS


def test_step_guide_is_a_compact_desktop_work_row():
    assert '"meta guide actions"' in CSS
    assert ".admin-step-flow__guide > div:not(:nth-child(2))" in CSS
    assert "min-height: 96px" in CSS


def test_desktop_scale_does_not_override_mobile_rules():
    assert "max-width" not in CSS.split("@media (min-width: 1000px)", 1)[0]
    assert 'import "../admin-desktop-v2650.css";' in LAYOUT
