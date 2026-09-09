from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v605_version_contract():
    expected = '2026.09.09-605-THEME-ARCHITECTURE-REBUILD'
    assert VERSION == expected
    assert expected in APP
    assert expected in (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_v605_authoritative_theme_is_last_cascade():
    assert 'v605 — authoritative CupNavi design-system cascade' in APP
    assert APP.index('v605 — authoritative CupNavi design-system cascade') > APP.index('v604 visual QA')
    assert '--cn-bg:#06111a' in APP
    assert '--cn-surface:#0a1b27' in APP
    assert '--cn-text:#f1f8fb' in APP
    assert 'html,body,[data-testid="stAppViewContainer"],body .stApp' in APP
    assert 'body [data-testid="stSidebar"]' in APP


def test_v605_has_readable_disabled_and_legacy_controls():
    assert 'button:disabled{opacity:1!important' in APP
    assert 'color:#76909e!important' in APP
    assert '[data-testid="stVerticalBlockBorderWrapper"]' in APP
    assert '[data-testid="stExpander"]' in APP
    assert '[data-testid="stAlert"]' in APP


def test_v605_compacts_desktop_flow_to_single_rail():
    block = APP[APP.index('with st.container(key=f"admin_full_flow_desktop_{tid}")'):APP.index('with st.container(key=f"admin_flow_mobile_{tid}")')]
    assert 'st.columns(len(_BEGINNER_JOURNEY), gap="small")' in block
    assert 'for _journey_row in' not in block
    assert 'Steg {_idx} av {len(_BEGINNER_JOURNEY)}' in block


def test_v605_keeps_mobile_flow_and_texttv_distinct():
    assert 'admin_flow_mobile_' in APP
    assert 'body .stApp .cn-texttv-table' in APP
    assert 'background:#020607!important' in APP
    assert 'body [data-baseweb="calendar"]{background:#fff!important;}' in APP
