from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")


def test_first_run_primary_cta_starts_at_cupinfo():
    assert '"Fortsätt med Cupinfo →"' in APP
    assert 'args=("Cupinställningar",)' in APP
    assert '"Läs in foto/PDF →"' in APP


def test_next_step_does_not_skip_pitches():
    pitch_gate = 'elif int(_flow_counts["pitches_n"] or 0) == 0:'
    schedule_gate = 'elif _flow_scheduled == 0 or bool(tournament["schedule_dirty"]):'
    assert pitch_gate in APP
    assert APP.index(pitch_gate) < APP.index(schedule_gate)
    assert '"Lägg till planer och tider"' in APP


def test_beginner_copy_uses_all_seven_steps():
    assert 'Lägg till lag → Grupper → Planer & tider → Schema → Kontroll → Publicera.' in SETUP
