from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
OVERVIEW = (ROOT / "cupnavi_core" / "admin_overview.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")

def test_programmatic_admin_navigation_survives_guided_widget_rebuild():
    assert 'pending_admin_page_{tid}' in APP
    assert '_pending_admin_page = st.session_state.pop' in APP
    assert 'st.session_state[f"admin_flow_page_{tid}_{_pending_step}"] = _pending_admin_page' in APP

def test_existing_schedule_is_never_described_as_automatic_regeneration():
    assert 'Nästa steg: granska schemaändring' in OVERVIEW
    assert 'CupNavi ändrar ingenting automatiskt' in OVERVIEW

def test_existing_unplayed_schedule_requires_explicit_confirmation_before_rebuild():
    assert 'Det finns redan ett schema. Om du skapar om det kan matchtider, planer och domartilldelning ändras.' in SCHEDULE
    assert 'Jag förstår att befintliga schematider kan ersättas' in SCHEDULE
    assert '_schedule_action_disabled = create_disabled or (_regenerating_unplayed_schedule and not _confirm_regenerate)' in SCHEDULE
