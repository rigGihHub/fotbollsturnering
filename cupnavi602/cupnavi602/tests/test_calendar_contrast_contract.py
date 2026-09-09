from pathlib import Path
APP = Path(__file__).resolve().parents[1] / "app.py"

def test_calendar_portal_has_high_contrast_override():
    text = APP.read_text(encoding="utf-8")
    assert "CUPNAVI CALENDAR FINAL OVERRIDE" in text
    assert '[data-baseweb="popover"]' in text
    assert '[data-baseweb="calendar"] abbr' in text
    assert '[data-baseweb="calendar"] [role="gridcell"]' in text
    assert 'background:#ffffff !important;' in text
    assert 'color:#172033 !important;' in text
