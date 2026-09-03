from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VIEW = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v392_version():
    assert VERSION == "2026.09.03-414-PITCH-TIMING-MODE"
    assert 'APP_BUILD_VERSION = "2026.09.03-414-PITCH-TIMING-MODE"' in APP


def test_new_tournament_enters_wizard_mode():
    assert 'st.session_state["new_tournament_setup_mode"] = "new"' in APP
    assert 'new_tournament_wizard_step_' in APP
    assert 'render_new_tournament_wizard_module' in APP


def test_existing_tournament_settings_keep_full_editor():
    assert 'st.session_state["new_tournament_setup_mode"]="edit"' in APP
    assert 'if st.session_state.get("new_tournament_setup_mode") == "new":' in APP
    assert 'return render_initial_tournament_setup_module(tournament_id, tournament, deps=deps)' in APP


def test_wizard_is_five_step_and_hands_off_to_teams():
    assert 'labels = ["Typ", "Deltagare", "Planer & tider", "Upplägg", "Klart"]' in VIEW
    assert 'Steg {step} av 5' in VIEW
    assert 'Fortsätt → Lägg till lag' in VIEW
    assert 'st.session_state[f"admin_page_{tournament_id}"] = "Lag"' in VIEW


def test_wizard_requires_core_readiness_before_finish():
    assert 'address_ok = all(' in VIEW
    assert 'ready = all(ok for ok,_,_ in checks)' in VIEW
    assert 'disabled=not ready' in VIEW
