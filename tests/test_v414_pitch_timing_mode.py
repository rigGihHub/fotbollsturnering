from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIZARD = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v414_exposes_pitch_timing_choice_in_wizard():
    assert "Hur ska matchtiderna fördelas mellan planerna?" in WIZARD
    assert "Dynamiskt – varje plan använder nästa möjliga tid" in WIZARD
    assert "Synkroniserat – samma avsparkstider på alla planer" in WIZARD
    assert "UPDATE schedule_rules SET synchronized_pitch_times=?" in WIZARD


def test_v414_scheduler_honors_saved_choice():
    assert 'synchronized_pitch_times = bool(_row_value(rules, "synchronized_pitch_times", 0))' in APP
    assert "if synchronized_pitch_times:" in APP


def test_v414_version():
    assert VERSION == "2026.09.03-414-PITCH-TIMING-MODE"
