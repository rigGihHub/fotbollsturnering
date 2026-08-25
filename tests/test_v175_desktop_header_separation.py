from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.25-192-CI-HEALTH-DEPENDENCY"

def test_desktop_nav_has_real_vertical_safezone():
    assert ".cn-mode-nav-safezone{height:72px!important;display:block!important}" in APP
    assert "@media(max-width:900px)" in APP
    assert ".cn-mode-nav-safezone{height:0!important}" in APP

def test_brand_is_smaller_on_desktop():
    assert "max-width:min(185px, calc(100vw - 28px));" in APP
    assert "width:min(100%, 155px);" in APP

def test_top_padding_and_safezone_are_balanced():
    assert "padding-top:3.2rem !important;" in APP
    assert "cn-mode-nav-safezone" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
