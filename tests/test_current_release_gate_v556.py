from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.08-556-CONDITIONAL-HALFTIME-PERIOD-BREAK"


def test_release_files_are_current():
    assert VERSION in APP
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_halftime_copy_uses_halves_periods():
    assert "Paus mellan halvlekar/perioder" in APP
    assert "Paus mellan halvlekar/perioder" in SETUP
    assert 'number_input("Paus mellan perioder"' not in SETUP


def test_halftime_control_is_conditional_on_two_or_more_periods():
    assert "if int(edited_halves) >= 2:" in APP
    assert "if int(halves) >= 2:" in APP
    assert "if int(_halves_value) >= 2:" in SETUP
    assert "if int(_setup_halves_value) >= 2:" in SETUP


def test_v555_behaviour_is_retained():
    assert 'st.session_state[f"admin_page_{int(new_tournament_id)}"] = "Lag"' in APP
    assert 'synchronized_pitch_times INTEGER NOT NULL DEFAULT 1' in APP
    assert '(not consider_travel or not _addresses_to_verify)' in SETUP
