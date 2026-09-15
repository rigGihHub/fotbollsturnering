from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADMIN = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")
HOME_CSS = (ROOT / "frontend-next/src/app/home.module.css").read_text(encoding="utf-8")


def test_overview_loads_authoritative_schedule_state():
    assert "type ScheduleOverview" in ADMIN
    assert "setScheduleOverview(scheduleData)" in ADMIN
    assert "${nextCupId}/schedule" in ADMIN
    assert 'if(activeStep==="overview")void refreshScheduleOverview()' in ADMIN


def test_next_action_distinguishes_schedule_states():
    for expected in (
        "Skapa matchschemat",
        "Schemalägg alla matcher",
        "Rätta schemakrockarna",
        "Godkänn det ändrade schemat",
        "Kontrollera och publicera",
    ):
        assert expected in ADMIN
    assert '{name:"Schema",status:scheduleStatusLabel' in ADMIN


def test_home_css_uses_supported_flex_alignment():
    assert "align-items:end" not in HOME_CSS
    assert "align-items:flex-end" in HOME_CSS
