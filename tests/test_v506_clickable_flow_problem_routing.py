from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
FLOW = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")


def test_planning_flow_is_real_navigation():
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Lag"' in APP
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Grupper"' in APP
    assert 'current_step="Schema"' in SCHEDULE
    assert 'render_clickable_planning_flow(st, tid=tid, current_step="Kontroll"' in APP
    assert '"Cupinfo": "Cupinställningar"' in FLOW
    assert '"Publicera": "Kontroller"' in FLOW


def test_schedule_blockers_link_to_the_fix_location():
    assert 'render_problem_actions(' in SCHEDULE
    assert 'needs_teams=not participant_list_complete or bool(unassigned_count)' in SCHEDULE
    assert 'needs_groups=not bool(schedule_groups) or bool(too_small_groups) or bool(unassigned_count)' in SCHEDULE
    assert 'needs_setup=not playoff_model_ready or bool(playoff_setup_error)' in SCHEDULE
    assert '"Gå till Lag →"' in FLOW
    assert '"Gå till Grupper →"' in FLOW
    assert '"Gå till Cupinfo →"' in FLOW
