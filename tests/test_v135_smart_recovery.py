from pathlib import Path
APP=Path("app.py").read_text(encoding="utf-8")
SETUP=Path("cupnavi_core/initial_setup_view.py").read_text(encoding="utf-8")

def test_recovery_actions_apply_and_regenerate():
    assert "def _rerun_schedule_after_recovery" in APP
    assert "Tillämpa +" in APP and "och generera om" in APP
    assert "Ta bort reservationerna och generera om" in APP
    assert "Lägg till 1 plan och generera om" in APP
    assert "Nästa bästa lösning visas nedan" in APP

def test_soft_late_preference_not_claimed_as_blocking_solution():
    assert "Detta är en mjuk prioritering och blockerar inte i sig schemaläggningen" in APP

def test_pitch_naming_is_explicit_in_capacity_setup():
    assert "Namnge planer/spelytor" in SETUP
    assert "Huvudplan, Hall A eller Arena 2" in SETUP
