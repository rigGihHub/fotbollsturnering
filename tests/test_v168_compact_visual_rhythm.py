from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
STYLE=(ROOT/"cupnavi_core/style_system.py").read_text(encoding="utf-8")
UI=APP+"\n"+STYLE
R="2026.09.03-427-TRAVEL-RULES-FLOW"

def test_public_status_is_integrated_into_hero():
    assert "cn-hero-status" in UI
    assert 'st.info("🔴 Cupen pågår")' not in APP
    assert "cn-hero-title-row" in UI

def test_redundant_mode_caption_is_removed():
    assert 'st.caption(tr("Välj läge"))' not in APP

def test_desktop_density_is_tighter_but_mobile_rules_remain():
    assert "padding-top:3.2rem !important;" in UI
    assert ".stApp .block-container{padding-top:.75rem!important" in UI
    assert '[data-testid="stVerticalBlock"]{gap:.42rem!important}' in UI
    assert "@media(max-width:760px)" in UI

def test_redundant_admin_heading_is_removed():
    assert "<div class='cn-admin-section-label'>" not in APP
    assert 'st.markdown(f"### {tr(\'Administration\')}")' not in APP

def test_recommended_action_is_single_row():
    assert "_next_copy_col, _next_button_col = st.columns([3, 2])" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
