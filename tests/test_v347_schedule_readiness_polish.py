from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert VERSION in APP

def test_expected_team_count_is_part_of_schedule_readiness():
    assert 'expected_team_count = int(tournament["expected_team_count"] or 0)' in SCHEDULE
    assert "participant_list_complete" in SCHEDULE
    assert "not participant_list_complete" in SCHEDULE

def test_schedule_readiness_has_five_visible_checks():
    assert '"Deltagarlista"' in SCHEDULE
    assert '"Grupper"' in SCHEDULE
    assert '"Gruppplacering"' in SCHEDULE
    assert '"Gruppstorlek"' in SCHEDULE
    assert '"Slutspelsmodell"' in SCHEDULE
    assert 'st.caption(f"Förkontroll · {ready_count}/{len(readiness_checks)} steg klara")' in SCHEDULE

def test_ready_signal_only_when_every_check_passes():
    assert "if ready_count == len(readiness_checks):" in SCHEDULE
    assert "Redo att skapa spelschema. CupNavi har allt grundunderlag som behövs." in SCHEDULE

def test_incomplete_participant_list_has_actionable_block_reason():
    assert 'problems.append(f"registrera alla lag ({registered_team_count}/{expected_team_count})")' in SCHEDULE
