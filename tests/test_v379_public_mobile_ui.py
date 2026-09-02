from pathlib import Path
from cupnavi_core.public_view_logic import public_navigation_specs

ROOT=Path(__file__).resolve().parents[1]
WORKSPACE=(ROOT/"cupnavi_core/public_workspace_view.py").read_text(encoding="utf-8")
FOLLOW=(ROOT/"cupnavi_core/public_team_follow_view.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text().strip()

def test_release_version():
    assert VERSION=="2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"

def test_public_navigation_is_task_first_and_short():
    specs=public_navigation_specs()
    assert [x[0] for x in specs]==["Matcher","Mitt lag","Tabeller","Slutspel","Info"]
    assert [x[2] for x in specs]==["Matcher","Mitt lag","Tabell","Slutspel","Information"]
    assert [x[1] for x in specs]==["matches","team","tables","playoffs","info"]

def test_public_navigation_keeps_native_fast_rerun():
    assert "st.segmented_control(" in WORKSPACE
    assert "on_change=_sync_public_primary_navigation" in WORKSPACE

def test_mitt_lag_is_visually_explained_without_new_queries():
    assert "cn-public-follow-label" in FOLLOW
    assert "Välj lag för att få nästa match, plan och viktig laginformation först." in FOLLOW
    assert 'favorite_selection = st.selectbox(' in FOLLOW

def test_mobile_navigation_and_team_card_have_responsive_styles():
    assert '[class*="st-key-cn_public_primary_nav_shell_"]' in STYLE
    assert "position:sticky" in STYLE
    assert ".cn-public-follow-anchor{" in STYLE
    assert ".cn-follow-shell{" in STYLE
    assert "@media(max-width:680px)" in STYLE
    assert "/* v385 — Logical flow + no-scroll public primary navigation */" in STYLE
    assert "min-width:0!important" in STYLE
