from pathlib import Path
APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")
def test_cross_browser_fallbacks_exist():
    assert "-webkit-backdrop-filter" in APP
    assert "@media(max-width:760px)" in APP
    assert "color-scheme:light" in APP
