from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_desktop_nav_has_compact_safezone():
    assert ".cn-mode-nav-safezone{height:24px!important;display:block!important}" in APP
    assert "max-width:430px!important" in APP
