from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VER=(ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
R=(ROOT/"VERSION.txt").read_text().strip()
def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in VER
def test_tighter_desktop_spacing():
    assert ".cn-flow-context{margin-top:0!important" in APP
def test_zero_height_helpers():
    assert ".cn-public-follow-anchor{height:0" in APP
    assert ".cn-share-inline-anchor{height:0" in APP
def test_clear_release_warning():
    assert "Releasefilerna är inte synkade" in APP
