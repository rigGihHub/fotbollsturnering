from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = "2026.09.10-612-SIGNATURE-ADMIN-STUDIO"

def test_canonical_versions_are_synced():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    text = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    assert f'APP_BUILD_VERSION = "{VERSION}"' in app
    assert f'APP_VERSION = "{VERSION}"' in core
    assert text == VERSION

def test_signature_admin_studio_css_contract():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    for token in ["cn612-create-cover", "cn612-admin-deck", "cn612-first-run", "--cn612-paper:#F3F0E6", "--cn612-tv:#020708"]:
        assert token in app

def test_creator_uses_signature_cover():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '<div class="cn612-create-cover">' in app
    assert "CN / NEW CUP" in app
    assert "Skapa din cup." in app

def test_admin_overview_uses_tournament_control_card():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert '<div class="cn612-admin-deck">' in app
    assert "Turneringskontroll" in app
    assert "html.escape(tournament['name'])" in app

def test_readability_contract_keeps_light_inputs_dark_text():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'color:var(--cn612-ink)!important' in app
    assert '[data-testid="stWidgetLabel"]' in app
