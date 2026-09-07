from pathlib import Path
SCHEDULE = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")

from cupnavi_core.version import APP_VERSION


def test_v420_version():
    assert APP_VERSION == "2026.09.07-519-BEGINNER-E2E-REGRESSION"


def test_schedule_workspace_keeps_six_step_planning_flow():
    src=SCHEDULE
    assert 'render_clickable_planning_flow(' in src
    assert 'current_step="Schema"' in src
    assert 'Fortsätt till Kontroll →' in src

def test_schedule_workspace_receives_navigation_callback():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'navigate_admin_page=_set_admin_page' in app
