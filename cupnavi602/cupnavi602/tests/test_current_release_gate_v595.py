from pathlib import Path
APP=Path("app.py").read_text()
SCHEDULE=Path("cupnavi_core/schedule_workspace_view.py").read_text()

def test_v595_version():
    assert 'APP_BUILD_VERSION = "2026.09.09-595-SCHEDULE-UX-VISUAL-PASS"' in APP

def test_v595_schedule_four_step_flow():
    for label in [
        "### 1. Vad vill du göra med schemat?",
        "### 2. Kontrollera att allt är redo",
        "### 3. Skapa, granska eller justera schemat",
        "### 4. Gå vidare till kontroll",
    ]:
        assert label in SCHEDULE

def test_v595_single_forward_handoff_and_safe_paths():
    assert 'v595_schedule_next_to_control_' in SCHEDULE
    assert 'schedule_flow_next_to_control_' not in SCHEDULE
    assert '← Till Domare' in SCHEDULE
    assert 'CupNavi skriver aldrig över ett befintligt schema automatiskt' in SCHEDULE
