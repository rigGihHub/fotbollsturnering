from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.08.28-249-PUBLIC-MATCH-RENDER-FIX"

def test_public_status_is_integrated_into_hero():
    assert "cn-hero-status" in APP
    assert 'st.info("🔴 Cupen pågår")' not in APP
    assert "cn-hero-title-row" in APP

def test_redundant_mode_caption_is_removed():
    assert 'st.caption(tr("Välj läge"))' not in APP

def test_desktop_density_is_tighter_but_mobile_rules_remain():
    assert "padding-top:3.2rem !important;" in APP
    assert ".stApp .block-container{padding-top:.75rem!important" in APP
    assert '[data-testid="stVerticalBlock"]{gap:.42rem!important}' in APP
    assert "@media(max-width:760px)" in APP

def test_admin_heading_is_compact():
    assert "cn-admin-section-label" in APP
    assert 'st.markdown(f"### {tr(\'Administration\')}")' not in APP

def test_recommended_action_is_single_row():
    assert "_next_copy_col, _next_button_col = st.columns([3, 2])" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
