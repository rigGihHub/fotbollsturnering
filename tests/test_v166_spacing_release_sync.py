from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VER=(ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
R="2026.08.25-167-PUBLIC-COMPETITION-NAV"

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in VER
    assert (ROOT/"VERSION.txt").read_text().strip()==R

def test_tighter_desktop_spacing():
    assert ".stApp .block-container{padding-top:1.05rem!important" in APP
    assert ".cn-flow-context{margin-top:2px!important" in APP
    assert "[data-testid=\"stVerticalBlock\"]{gap:.55rem!important}" in APP

def test_zero_height_helpers():
    assert ".cn-public-follow-anchor{height:0" in APP
    assert ".cn-share-toggle-anchor,.cn-share-panel-anchor{height:0" in APP

def test_clear_release_warning():
    assert "Releasefilerna är inte synkade" in APP
