from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
CORE_VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
SHELL = (ROOT / "cupnavi_core" / "public_shell_view.py").read_text(encoding="utf-8")
PRESENTATION = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")


def test_release_version_is_synchronized():
    assert VERSION == "2026.09.10-611-SIGNATURE-PUBLIC-STAGE"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in CORE_VERSION


def test_public_cover_has_signature_structure():
    for token in ("cn611-public-cover", "cn611-cover-kicker", "cn611-cover-footer", "MATCHDAY / 01"):
        assert token in SHELL or token in APP


def test_public_mobile_navigation_is_compact_and_scrollable():
    assert 'st-key-cn_public_primary_nav_shell_' in APP
    assert 'overflow-x:auto!important' in APP
    assert 'aria-pressed="true"' in APP


def test_desktop_playoff_uses_signature_card_and_texttv_score():
    assert "background:#020708" in PRESENTATION
    assert "clip-path:polygon" in PRESENTATION
    assert "classic-match.final-match" in PRESENTATION
    assert "border-bottom:3px solid #00a7b7" in PRESENTATION


def test_accessible_motion_contract_remains():
    assert "prefers-reduced-motion:reduce" in APP
    assert "transition:none!important" in APP
