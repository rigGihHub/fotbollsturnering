from pathlib import Path

APP = Path("app.py").read_text(encoding="utf-8")
WORKSPACE = Path("cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
VERSION = Path("VERSION.txt").read_text(encoding="utf-8").strip()


def test_v390_release_version():
    assert VERSION == "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"
    assert 'APP_BUILD_VERSION = "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"' in APP


def test_share_popover_activates_scoped_light_theme():
    render_start = APP.index("def render_public_share_control")
    render_end = APP.index("@st.cache_data", render_start)
    block = APP[render_start:render_end]
    assert "cn-share-popover-marker" in block
    assert '[data-testid="stPopoverBody"]:has(.cn-share-popover-marker)' in APP
    assert 'color:#174d2f!important' in APP


def test_toplists_are_discoverable_before_table_rendering():
    page_start = WORKSPACE.index('if public_page == "Tabeller":')
    page_end = WORKSPACE.index('if public_page == "Slutspel":', page_start)
    block = WORKSPACE[page_start:page_end]
    assert 'st.segmented_control(' in block
    assert '[tr("Tabeller"), tr("Topplistor")]' in block
    assert '"Visa individuella topplistor"' not in block
    selector_pos = block.index('st.segmented_control(')
    top_branch_pos = block.index('if competition_view == tr("Topplistor")')
    table_render_pos = block.index('forced_section=tr("Tabeller")')
    assert selector_pos < top_branch_pos < table_render_pos
