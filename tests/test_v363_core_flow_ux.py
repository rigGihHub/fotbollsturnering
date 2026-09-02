from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")


def test_team_page_prioritizes_minimum_required_action():
    assert '<div class="title">Lag</div>' in APP
    assert "Börja med lagnamnet" in APP
    assert "Skriv lagnamnet och spara. Resten kan kompletteras senare." in APP
    assert "Komplettera laget (valfritt)" in APP
    assert "Fortsätt till Grupper →" in APP


def test_group_page_shows_summary_before_details():
    assert "CupNavi rekommenderar" in APP
    assert 'metric("Grupper"' in APP
    assert "Visa vilka lag som hamnar i varje grupp" in APP
    assert "Använd CupNavis gruppindelning" in APP
    assert "Skapa grupper själv" in APP


def test_schedule_core_action_comes_before_optional_tools():
    assert "#### Nästa steg" in SCHEDULE
    assert "#### Schema" in SCHEDULE
    assert "Valfria schemaverktyg" in SCHEDULE
    assert SCHEDULE.index("#### Schema") < SCHEDULE.index("Valfria schemaverktyg")
    assert SCHEDULE.index("Valfria schemaverktyg") < SCHEDULE.index("Analysera schemakvalitet")
    assert "Behövs bara när ett redan skapat schema ska finjusteras." in SCHEDULE


def test_setup_uses_progressive_disclosure_wording():
    assert "### Rekommenderat upplägg" in SETUP
    assert '"Använd förslaget"' in SETUP
    assert '"Anpassa själv"' in SETUP
    assert '"Fler inställningar"' in SETUP
    assert "specialinställningar kan vänta" in SETUP


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.02-388-ADMIN-CORE-FLOW-CLEANUP"' in APP
