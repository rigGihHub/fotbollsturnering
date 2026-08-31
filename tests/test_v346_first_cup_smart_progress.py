from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_version():
    assert VERSION=="2026.08.31-353-GROUP-FLOW-PITCH-TIMING"
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP

def test_team_registration_has_real_progress_and_group_handoff():
    assert "participant_registration_complete" in APP
    assert '"Fortsätt → Skapa grupper"' in APP
    assert 'key=f"v346_teams_to_groups_{tid}"' in APP

def test_group_automation_waits_for_complete_participant_list():
    assert "_participant_registration_complete" in APP
    assert "CupNavi väntar med automatisk gruppindelning tills alla lag finns med." in APP
    smart_line = "_smart_group_plan(teams, class_rows)"
    assert smart_line in APP
    assert "teams and _participant_registration_complete and _existing_groups_count == 0" in APP

def test_groups_have_back_to_teams_and_forward_to_schedule_ctas():
    assert '"Fortsätt lägga till lag"' in APP
    assert 'key=f"v346_groups_back_to_teams_{tid}"' in APP
    assert '"Fortsätt till Schema →"' in APP
    assert 'key=f"v346_groups_to_schedule_{tid}"' in APP

def test_group_completion_requires_no_unassigned_teams():
    assert "_unassigned_after_assignment == 0" in APP
    assert '"### ✓ Gruppindelningen är klar"' in APP
