from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v603_version_contract():
    assert VERSION == '2026.09.09-603-GLOBAL-DARK-SHELL-ACCESS-HOTFIX'
    assert VERSION in (ROOT / 'cupnavi_core/version.py').read_text(encoding='utf-8')


def test_v603_dark_shell_is_global_and_final():
    assert 'GLOBAL DARK SPORT SHELL' in APP
    assert 'v603 final cascade' in APP
    assert '--cn-bg:#06111a' in APP
    assert 'body .stApp{background:linear-gradient(180deg,#06111a,#07151f)' in APP
    assert 'body .stApp [data-testid="stSidebar"]{background:#071722' in APP


def test_v603_invitation_schema_repairs_on_startup():
    assert 'ensure_v34_schema_compat(con)' in APP
    assert 'stale/partially migrated Turso schema' in APP


def test_v603_invitation_schema_helper_creates_expected_columns():
    from cupnavi_core.migrations import ensure_v34_schema_compat
    con = sqlite3.connect(':memory:')
    con.execute('PRAGMA foreign_keys=OFF')
    ensure_v34_schema_compat(con)
    cols = {row[1] for row in con.execute('PRAGMA table_info(tournament_admin_invitations)')}
    assert {'id','tournament_id','email','display_name','created_at','expires_at','accepted_at','revoked_at'} <= cols
