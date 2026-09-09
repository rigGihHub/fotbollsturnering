from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")


def test_v511_version():
    assert "2026.09.07-525-OPTIONAL-REFEREE-SETUP" in VERSION
    assert 'APP_BUILD_VERSION = "2026.09.07-525-OPTIONAL-REFEREE-SETUP"' in APP


def test_existing_tournament_setup_is_reachable_from_sidebar():
    assert '"⚙️ Ändra cupsetup"' in APP
    assert 'st.session_state["new_tournament_setup_mode"] = "edit"' in APP
    assert 'st.session_state["new_tournament_setup_id"] = int(tid)' in APP


def test_existing_setup_can_edit_dates_safely():
    assert 'st.markdown("### Cupdatum")' in SETUP
    assert '"Spara cupdatum"' in SETUP
    assert 'UPDATE tournaments SET tournament_date=?, start_date=?, end_date=?, schedule_dirty=1 WHERE id=?' in SETUP
    assert 'Ett nytt cupdatum flyttar inte matcherna automatiskt.' in SETUP
    assert 'UPDATE matches SET schedule_published=0 WHERE tournament_id=?' in SETUP
