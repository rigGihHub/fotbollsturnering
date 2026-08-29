from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
def test_cross_browser_fallbacks_exist():
    assert "-webkit-backdrop-filter" in STYLE
    assert "@media(max-width:760px)" in STYLE
    assert "color-scheme:light" in STYLE
