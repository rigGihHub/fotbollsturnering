from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = '2026.09.09-602-FULL-VISUAL-THEME-ACCESS-FIX'


def test_version_synced():
    assert ROOT.joinpath('VERSION.txt').read_text(encoding='utf-8').strip() == VERSION
    assert VERSION in ROOT.joinpath('cupnavi_core/version.py').read_text(encoding='utf-8')
    assert VERSION in APP


def test_full_visual_theme_contract():
    for token in [
        'cupnavi-v602-full-theme', '--cn-bg:#06111d', '--cn-cyan:#19d7f2',
        '[data-testid="stSidebar"]', '[data-baseweb="input"]', '.stTabs [data-baseweb="tab"]'
    ]:
        assert token in APP


def test_pending_invitation_read_uses_db_clock_not_python_datetime_binding():
    start = APP.index('_pending_invites = all_rows(')
    end = APP.index('if _pending_invites:', start)
    block = APP[start:end]
    assert "strftime('%Y-%m-%dT%H:%M:%S','now')" in block
    assert '(tid,),' in block
    assert 'expires_at>?' not in block
    assert 'datetime.now().isoformat' not in block


def test_kit_search_and_texttv_features_remain_present():
    assert '⚡ Snabbsök tröjor för alla lag' in APP
    assert 'Tröjfärger' in APP
    assert 'Text-TV' in APP or 'TEXT-TV' in APP
