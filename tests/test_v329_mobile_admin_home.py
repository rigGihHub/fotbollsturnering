from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_release_version():
    assert VERSION == "2026.08.31-354-ADDRESS-READINESS-FIX"

def test_mobile_admin_home_uses_single_primary_next_action():
    start=APP.index('elif admin_page == "Adminöversikt":'); end=APP.index('if admin_page == "Cupinställningar":', start); block=APP[start:end]
    assert '#### 📱 Snabbadmin' not in block
    assert 'key=f"dashboard_next_step_{tid}"' in block
    assert 'type="primary"' in block
    assert 'use_container_width=True' in block

def test_mobile_admin_home_reuses_existing_navigation_only():
    start=APP.index('with st.container(border=True):', APP.index('elif admin_page == "Adminöversikt":')); end=APP.index('checkin_enabled =', start); block=APP[start:end]
    assert 'on_click=_set_admin_page' in block
    assert 'run(' not in block and 'UPDATE ' not in block and 'INSERT ' not in block and 'DELETE ' not in block

def test_mobile_tournament_switcher_and_creation_remain_available():
    assert 'key="main_active_tournament_selector"' in APP
    assert 'with st.expander("➕ Ny turnering", expanded=False)' in APP
