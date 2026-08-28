from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
CFG = Path('.streamlit/config.toml').read_text(encoding='utf-8')


def test_public_nav_is_single_link_based_sticky_control():
    assert "cn-public-section-nav" in APP
    assert "role='button'" in APP
    block = APP[APP.index('# v1.266: en enda länkbaserad cupnavigation'):APP.index('def _filter_public_matches')]
    assert 'st.columns(len(nav_specs))' not in block
    assert 'nav_col.button(' not in block
    assert block.count("cn-mobile-bottom-nav cn-public-section-nav") == 1


def test_android_summary_uses_900px_responsive_breakpoint():
    start=APP.index('def inject_v266_public_mobile_css')
    end=APP.index('\ninject_v266_public_mobile_css()', start)
    css=APP[start:end]
    assert '@media(max-width:900px)' in css
    assert 'grid-template-columns:repeat(2,minmax(0,1fr))' in css
    assert '.cn-public-highlights' in css
    assert 'min-width:0 !important' in css


def test_streamlit_toolbar_is_minimized_and_fork_chrome_hidden():
    assert 'toolbarMode = "minimal"' in CFG
    assert '[data-testid="stToolbar"]' in APP
    assert '.stAppDeployButton' in APP
