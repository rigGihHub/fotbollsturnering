from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")

def test_v512_version():
    assert "2026.09.07-519-BEGINNER-E2E-REGRESSION" in VERSION
    assert 'APP_BUILD_VERSION = "2026.09.07-519-BEGINNER-E2E-REGRESSION"' in APP

def test_schema_has_explicit_next_control_button():
    assert '"Fortsätt till Kontroll →"' in SCHEDULE
    assert 'args=("Kontroll",)' in SCHEDULE

def test_legacy_photo_schedule_recovery_is_visible():
    assert 'expanded=True' in SCHEDULE
    assert 'ser 0 schemalagda matcher här' in SCHEDULE
    assert 'Du kan ändå gå vidare till Kontroll' in SCHEDULE
