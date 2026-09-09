from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "public_presentation_view.py").read_text(encoding="utf-8")

def test_v592_build_version():
    assert 'APP_BUILD_VERSION = "2026.09.09-592-TEXTTV330-FUTURE-TABLES"' in APP

def test_v592_texttv_black_table_and_headers():
    assert 'background:#050705' in VIEW
    assert '<th>Pl</th><th>Lag</th><th>S</th><th>V</th><th>O</th><th>F</th>' in VIEW
    assert 'font-variant-numeric:tabular-nums' in VIEW

def test_v592_mobile_and_accessible_qualification():
    assert '@media(max-width:600px)' in VIEW
    assert 'Qualification is communicated with accent + label, never colour alone.' in VIEW
    assert 'qualifier-desktop' in VIEW and 'qualifier-mobile' in VIEW
