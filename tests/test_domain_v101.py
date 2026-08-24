from pathlib import Path

from cupnavi_core.config import OFFICIAL_PUBLIC_BASE_URL, PUBLIC_BASE_URL, LEGACY_STREAMLIT_BASE_URL
from cupnavi_core.version import APP_VERSION


def test_official_domain_is_cup_navi_com():
    assert OFFICIAL_PUBLIC_BASE_URL == "https://cup-navi.com"
    assert PUBLIC_BASE_URL == "https://cup-navi.com"
    assert LEGACY_STREAMLIT_BASE_URL == "https://cupnavi.streamlit.app"


def test_v101_version_files_match():
    assert APP_VERSION == "2026.08.24-101-DOMAIN-FOUNDATION"
    assert Path("VERSION.txt").read_text(encoding="utf-8").strip() == APP_VERSION
    text = Path("app.py").read_text(encoding="utf-8")
    assert f'APP_BUILD_VERSION = "{APP_VERSION}"' in text


def test_public_urls_are_centralized():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "PUBLIC_APP_URL = PUBLIC_BASE_URL.rstrip" in text
    assert '"https://cupnavi.streamlit.app/"' not in text
    assert "def public_cup_url(tournament_id):" in text


def test_release_mismatch_help_is_actionable():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "cupnavi_core/version.py:" in text
    assert "Lägg in hela releasepaketet i GitHub, inte bara app.py." in text
    assert "Starta sedan om Streamlit-appen" in text
