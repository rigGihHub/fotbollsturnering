from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v501_release_version():
    assert VERSION == "2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"


def test_new_tournament_wizard_forces_readable_light_workspace():
    assert '[data-testid="stAppViewContainer"]' in VIEW
    assert '.stMainBlockContainer {' in VIEW
    assert 'background:#f6f8f7 !important;' in VIEW
    assert 'color:#172033 !important;' in VIEW
    assert '[data-testid="stCaptionContainer"]' in VIEW
    assert '[data-testid="stWidgetLabel"]' in VIEW
