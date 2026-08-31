from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
UX=(ROOT/"cupnavi_core/ux2.py").read_text(encoding="utf-8")
VERSION="2026.08.31-349-BEGINNER-FIRST-RUN"

def overview_block():
    start=APP.index('elif admin_page == "Adminöversikt":'); end=APP.index('if admin_page == "Cupinställningar":', start); return APP[start:end]

def test_version_sync():
    assert (ROOT/"VERSION.txt").read_text().strip()==VERSION
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in (ROOT/"cupnavi_core/version.py").read_text()

def test_admin_has_five_simplified_top_groups():
    nav=APP[APP.index('ADMIN_NAV_GROUPS = ['):APP.index('ADMIN_NAV = [')]
    for group in ('Översikt','Deltagare','Matcher','Organisation','Mer'):
        assert f'("{group}",' in nav
    assert '("Kommunikation",' not in nav

def test_overview_has_one_primary_next_step_and_compact_flow():
    block=overview_block()
    assert block.count('key=f"dashboard_next_step_{tid}"')==1
    assert 'st.markdown("#### Din väg till en färdig cup")' in block
    assert '("Lag", teams_n > 0)' in block
    assert '("Publicerad", bool(tournament["is_published"]))' in block

def test_duplicate_overview_surfaces_are_removed():
    block=overview_block()
    for duplicate in ('#### 📱 Snabbadmin','Förberedelser i detalj','Driftstatus','Genvägar & publik vy','Checklista inför cupstart','cn-progress-hero','build_status_cards_html(','build_workflow_html('):
        assert duplicate not in block

def test_advanced_overview_capabilities_are_preserved_but_opt_in():
    block=overview_block()
    assert '"Visa fler verktyg på översikten"' in block
    advanced=block.index('if show_overview_advanced:')
    assert block.index('with st.expander("⚖️ Fairnessanalys", expanded=False):') > advanced
    assert block.index('show_direct_edit = st.toggle(') > advanced
    assert '### 🎛️ Cup Control Center' in block

def test_primary_match_navigation_deemphasizes_events_and_statistics():
    primary=APP[APP.index('_ADMIN_PRIMARY_PAGES_BY_GROUP = {'):APP.index('def _admin_nav_item_is_active')]
    assert '"Matcher": {"Skapa och publicera schema", "Matcher och resultat", "Slutspel"}' in primary
    assert '"Matchhändelser"' not in primary
    assert '"Tabeller"' not in primary

def test_ux_helper_matches_new_information_architecture():
    assert '("Mer", [])' in UX
    assert '("Organisation", ["Domare", "Funktionärer", "Sponsorer", "Erbjudanden"])' in UX
