
from pathlib import Path

APP=(Path(__file__).resolve().parents[1]/"app.py").read_text(encoding="utf-8")


def _admin_overview():
    start=APP.index('elif admin_page == "Adminöversikt":')
    end=APP.index('if admin_page == "Cupinställningar":',start)
    return APP[start:end]


def test_schedule_status_reuses_flow_counts():
    region=APP[APP.index("admin_page = st.session_state[admin_page_key]"):]
    assert "current_schedule_scheduled = _flow_scheduled" in region
    assert "sidebar_scheduled = _flow_scheduled" in region
    assert "SELECT schedule_dirty,(SELECT COUNT(*) FROM matches" not in region


def test_admin_overview_reuses_loaded_rules_and_workflow_counts():
    block=_admin_overview()
    assert "sidebar_rules=sidebar_rules" in block
    assert "ux_counts = _v139_counts" in block
    assert block.count("_admin_workflow_counts(tid)") == 1


def test_admin_overview_batches_class_team_counts():
    block=_admin_overview()
    assert "GROUP BY competition_class_id" in block
    assert "_class_team_counts" in block
    assert "SELECT COUNT(*) AS n FROM teams WHERE tournament_id=? AND competition_class_id=?" not in block
