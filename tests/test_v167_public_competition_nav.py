from pathlib import Path
from cupnavi_core.public_view_logic import public_navigation_specs, public_section_for_page
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.28-249-PUBLIC-MATCH-RENDER-FIX"

def test_public_has_clear_competition_navigation():
    specs=public_navigation_specs()
    assert [item[0] for item in specs] == ["Matcher","Tabeller","Slutspel","Statistik","Info"]
    assert [item[2] for item in specs] == ["Schema & resultat","Tabeller","Slutspel","Statistik","Cupinfo"]

def test_sections_have_distinct_urls():
    assert public_section_for_page("Tabeller") == "tables"
    assert public_section_for_page("Slutspel") == "playoffs"
    assert public_section_for_page("Statistik") == "stats"

def test_public_sections_render_directly_without_second_level_segmented_control():
    assert 'forced_section=tr("Tabeller")' in APP
    assert 'forced_section=tr("Slutspel")' in APP
    assert 'forced_section=tr("Topplistor")' in APP

def test_mobile_bottom_nav_matches_competition_flow():
    specs=public_navigation_specs()
    assert [item[3] for item in specs] == ["Schema","Tabeller","Slutspel","Statistik","Cupinfo"]
    assert [item[1] for item in specs] == ["matches","tables","playoffs","stats","info"]

def test_info_uses_same_cupinfo_profile():
    assert ("Info", "info", "Cupinfo", "Cupinfo") in public_navigation_specs()

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
