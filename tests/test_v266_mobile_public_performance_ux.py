from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
STYLE = Path('cupnavi_core/style_system.py').read_text(encoding='utf-8')
PUBLIC_NAV = Path('cupnavi_core/public_navigation_view.py').read_text(encoding='utf-8')
CFG = Path('.streamlit/config.toml').read_text(encoding='utf-8')


def test_public_nav_is_single_link_based_sticky_control():
    assert "cn-public-section-nav" in PUBLIC_NAV
    assert "role='button'" in PUBLIC_NAV
    assert 'st.columns(' not in PUBLIC_NAV
    assert '.button(' not in PUBLIC_NAV
    assert PUBLIC_NAV.count("cn-mobile-bottom-nav cn-public-section-nav") == 1
    assert "build_public_navigation_html(" in APP


def test_android_summary_uses_900px_responsive_breakpoint():
    start=STYLE.index('def inject_v266_public_mobile_css')
    css=STYLE[start:]
    assert '@media(max-width:900px)' in css
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in css
    assert '.cn-public-highlights' in css
    assert 'min-width:0 !important' in css


def test_streamlit_toolbar_is_minimized_and_fork_chrome_hidden():
    assert 'toolbarMode = "minimal"' in CFG
    assert '[data-testid="stToolbar"]' in STYLE
    assert '.stAppDeployButton' in STYLE
