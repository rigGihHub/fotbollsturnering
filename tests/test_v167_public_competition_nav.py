from pathlib import Path
from cupnavi_core.public_view_logic import public_navigation_specs, public_section_for_page
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
R="2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"

def test_public_has_clear_competition_navigation():
    specs=public_navigation_specs()
    assert [item[0] for item in specs] == ["Matcher","Mitt lag","Tabeller","Slutspel","Info"]
    assert [item[2] for item in specs] == ["Matcher","Mitt lag","Tabell","Slutspel","Information"]

def test_sections_have_distinct_urls():
    assert public_section_for_page("Tabeller") == "tables"
    assert public_section_for_page("Slutspel") == "playoffs"
    assert public_section_for_page("Mitt lag") == "team"

def test_public_sections_render_directly_without_second_level_segmented_control():
    assert 'forced_section=tr("Tabeller")' in WORKSPACE
    assert 'forced_section=tr("Slutspel")' in WORKSPACE
    assert 'forced_section=tr("Topplistor")' in WORKSPACE

def test_mobile_bottom_nav_matches_competition_flow():
    specs=public_navigation_specs()
    assert [item[3] for item in specs] == ["Matcher","Mitt lag","Tabell","Slutspel","Info"]
    assert [item[1] for item in specs] == ["matches","team","tables","playoffs","info"]

def test_info_uses_same_cupinfo_profile():
    assert ("Info", "info", "Information", "Info") in public_navigation_specs()

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
