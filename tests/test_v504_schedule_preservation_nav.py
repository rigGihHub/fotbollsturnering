from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "cupnavi_core" / "admin_overview.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")

def test_programmatic_admin_navigation_survives_guided_widget_rebuild():
    flow=(ROOT/'cupnavi_core'/'planning_flow_nav.py').read_text(encoding='utf-8')
    assert 'navigate_admin_page(target_page)' in flow
    assert 'planning_control_focus_' in flow

def test_existing_schedule_is_never_described_as_automatic_regeneration():
    assert 'Nästa steg: granska schemaändring' in OVERVIEW
    assert 'CupNavi ändrar ingenting automatiskt' in OVERVIEW

def test_existing_unplayed_schedule_requires_explicit_confirmation_before_rebuild():
    assert '_regenerating_unplayed_schedule = bool(scheduled_total > 0 and not played_result_total)' in SCHEDULE
    assert '_confirm_regenerate = st.checkbox(' in SCHEDULE
    assert '_schedule_action_disabled = _regenerating_unplayed_schedule and not _confirm_regenerate' in SCHEDULE

