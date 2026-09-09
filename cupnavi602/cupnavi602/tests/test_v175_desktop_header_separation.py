from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
def test_desktop_nav_has_compact_safezone():
    assert ".cn-mode-nav-safezone{height:24px!important;display:block!important}" in STYLE
    assert "max-width:430px!important" in STYLE
