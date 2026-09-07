from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v502_release_version():
    assert VERSION == '2026.09.07-510-MANUAL-IMPORTED-SCHEDULE-EDIT'
    assert 'APP_BUILD_VERSION = "2026.09.07-510-MANUAL-IMPORTED-SCHEDULE-EDIT"' in APP


def test_admin_uses_one_guided_five_step_flow():
    assert '"Deltagare": "1 Deltagare"' in APP
    assert '"Planer & tider": "2 Planer & tider"' in APP
    assert '"Upplägg": "3 Upplägg"' in APP
    assert '"Organisation & koder": "4 Organisation & koder"' in APP
    assert '"Publicera & cupdag": "5 Publicera"' in APP
    assert 'Fortsätt bygga cupen' in APP
    assert '"Fler verktyg"' not in APP[APP.index('# v502: one guided admin flow'):APP.index('def _open_admin_search_hit')]


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
