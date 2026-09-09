from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
MATCH=(Path(__file__).resolve().parents[1]/"cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_desktop_public_density_pass_exists():
    assert "PUBLIC DENSITY & HIERARCHY V192" in APP
    assert ".cn-mode-nav-safezone{height:8px!important}" in APP
    assert ".cup-hero{" in APP
    assert "padding:10px 16px!important" in APP

def test_completed_match_cards_are_denser():
    assert ".public-match-card{" in APP
    assert "padding:8px 10px!important" in APP
    assert "font-size:14px!important" in APP
    assert "margin-top:4px!important" in APP

def test_enabled_weather_never_disappears_silently():
    assert 'weather_status = "Prognos visas för kommande matcher inom 16 dagar."' in MATCH
    assert "if show_weather and weather_text else \"\"" in MATCH
