from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text()

def test_v602_version_synced():
    v = '2026.09.09-602-FULL-VISUAL-THEME-ACCESS-FIX'
    assert (ROOT/'VERSION.txt').read_text().strip() == v
    assert v in (ROOT/'cupnavi_core/version.py').read_text()
    assert v in APP

def test_pending_invite_query_uses_db_clock_and_single_binding():
    block = APP[APP.index('_pending_invites = all_rows('):APP.index('if _pending_invites:', APP.index('_pending_invites = all_rows('))]
    assert "strftime('%Y-%m-%dT%H:%M:%S','now')" in block
    assert '(tid,),' in block
    assert 'datetime.now().isoformat' not in block

def test_full_dark_theme_is_final_shell_override():
    assert 'cupnavi-v602-full-theme' in APP
    for token in ['--cn-bg:#06111d','[data-testid="stSidebar"]','background:linear-gradient(180deg','#19d7f2']:
        assert token in APP
