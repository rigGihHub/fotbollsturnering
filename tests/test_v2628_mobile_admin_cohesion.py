from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SHELL=(ROOT/"frontend-next/src/components/admin-auth-shell.tsx").read_text(encoding="utf-8")
CSS=(ROOT/"frontend-next/src/app/admin-mobile-cohesion-v2628.css").read_text(encoding="utf-8")

def test_recovery_overlay_is_not_mounted_in_normal_admin_flow():
    assert "ImportRecoveryGuard" not in SHELL

def test_mobile_step_guide_is_single_column_and_primary_action_is_full_width():
    assert "grid-template-columns:1fr!important" in CSS
    assert ".admin-step-flow__actions .is-primary" in CSS
    assert "width:100%!important" in CSS

def test_mobile_admin_uses_deliberate_type_scale():
    for selector in (".admin-pagehead h1", ".admin-panel h2", ".admin-form-grid label", ".admin-sidebar nav a"):
        assert selector in CSS
