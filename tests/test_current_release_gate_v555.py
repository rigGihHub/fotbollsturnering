from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
WIZ = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
MIG = (ROOT / "cupnavi_core" / "migrations.py").read_text(encoding="utf-8")
VERSION = "2026.09.08-555-CREATION-HANDOFF-DEFAULT-SYNC-OPTIONAL-ADDRESSES"


def test_release_files_are_current():
    assert VERSION in APP
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_new_cup_hands_off_directly_to_lag():
    assert 'st.session_state[f"admin_page_{int(new_tournament_id)}"] = "Lag"' in APP
    assert 'st.session_state[f"pending_admin_page_{int(new_tournament_id)}"] = "Lag"' in APP
    assert 'st.session_state.pop("new_tournament_setup_id", None)' in APP


def test_synchronized_pitch_times_are_default_for_new_rules():
    assert 'synchronized_pitch_times INTEGER NOT NULL DEFAULT 1' in APP
    assert 'minimum_team_rest_minutes,synchronized_pitch_times' in APP
    assert ') VALUES(?,?,?,?,?,1)' in APP
    assert 'ADD COLUMN synchronized_pitch_times INTEGER NOT NULL DEFAULT 1' in MIG


def test_unverified_addresses_only_block_when_used_in_planning():
    assert '(not _travel_on or unverified == 0)' in WIZ
    assert 'Planadresser är frivilliga och blockerar inte nästa steg' in WIZ
    assert '(not consider_travel or not _addresses_to_verify)' in SETUP
    assert 'Använd planadresser/restid i planeringen' in SETUP
