from pathlib import Path

from cupnavi_core.version import APP_VERSION


def test_v420_version():
    assert APP_VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_schedule_workspace_keeps_six_step_planning_flow():
    src = Path("cupnavi_core/schedule_workspace_view.py").read_text(encoding="utf-8")
    assert 'Planeringsflöde · Spelschema' in src
    assert '["Grundsetup", "Lag", "Grupper", "Schema", "Kontroll", "Publicera"]' in src
    assert '← Till Grupper' in src
    assert 'Nästa steg: Kontroll' in src
    assert 'Steg 3 av 5 · Schema' not in src


def test_schedule_workspace_receives_navigation_callback():
    app = Path("app.py").read_text(encoding="utf-8")
    assert 'navigate_admin_page=_set_admin_page' in app
