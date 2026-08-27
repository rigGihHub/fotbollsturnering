
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def test_admin_team_edit_delete_use_optimistic_helpers():
    assert "def _admin_update_team_if_unchanged(" in APP
    assert "def _admin_delete_team_if_unchanged(" in APP
    lag=APP[APP.index('if admin_page == "Lag":'):APP.index('if admin_page == "Grupper":')]
    assert "_admin_update_team_if_unchanged(" in lag
    assert "_admin_delete_team_if_unchanged(" in lag


def test_admin_group_edit_delete_use_optimistic_helpers():
    groups=APP[APP.index('if admin_page == "Grupper":'):APP.index('if admin_page == "Trupper":')]
    assert "_admin_update_group_if_unchanged(" in groups
    assert "_admin_delete_group_if_unchanged(" in groups


def test_schedule_request_status_transition_is_guarded():
    assert "def _set_schedule_request_status_if_current(" in APP
    assert "_set_schedule_request_status_if_current(" in APP
    assert "Önskemålet ändrades av en annan administratör" in APP


def test_team_and_group_delete_helpers_are_tournament_scoped():
    team=APP[APP.index("def _admin_delete_team_if_unchanged"):APP.index("def _admin_group_snapshot")]
    group=APP[APP.index("def _admin_delete_group_if_unchanged"):APP.index("def _set_schedule_request_status_if_current")]
    assert "tournament_id=?" in team
    assert "tournament_id=?" in group
