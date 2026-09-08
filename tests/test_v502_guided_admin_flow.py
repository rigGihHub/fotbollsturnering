from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v502_release_version():
    assert VERSION == '2026.09.07-525-OPTIONAL-REFEREE-SETUP'
    assert 'APP_BUILD_VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"' in APP


def test_admin_uses_one_guided_five_step_flow():
    flow=(ROOT/'cupnavi_core'/'planning_flow_nav.py').read_text(encoding='utf-8')
    assert 'FLOW_STEPS = ["Cupinfo", "Lag", "Grupper", "Planer & tider", "Schema", "Kontroll", "Publicera"]' in flow
    assert 'Din väg till publicerad cup' in APP

def test_sidebar_contains_rename_and_delete_controls():
    assert 'with st.expander("Cupadministration", expanded=False):' in APP
    assert '"Spara nytt namn"' in APP
    assert 'with st.expander("🗑️ Radera cup", expanded=False):' in APP
    assert '"Öppna papperskorgen"' in APP


def test_all_access_codes_are_in_one_page():
    start = APP.index('if admin_page == "Åtkomst & koder":')
    end = APP.index('if admin_page == "Domare":', start)
    section = APP[start:end]
    assert 'st.header("Alla koder")' in section
    assert '"Matchrapportör"' in section
    assert '"Domare"' in section
    assert 'st.subheader("Lagkoder")' in section
    assert 'participant_access_credentials' in section


def test_referee_page_points_to_central_code_page():
    start = APP.index('if admin_page == "Domare":')
    section = APP[start:start + 3500]
    assert 'Organisation & koder → Alla koder' in section
    assert 'st.subheader("Åtkomstkoder")' not in section
