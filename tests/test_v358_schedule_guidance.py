from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load_module():
    spec = importlib.util.spec_from_file_location("schedule_workspace_view_v358", ROOT / "cupnavi_core" / "schedule_workspace_view.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_schedule_view_starts_with_beginner_guidance():
    assert "Steg 3 av 5" in VIEW
    assert "CupNavis rekommendation" in VIEW
    assert "Aktivt tidsläge:" in VIEW
    assert "Dynamiska plantider" in VIEW
    assert "Synkroniserade plantider" in VIEW


def test_next_step_recommends_schedule_when_ready():
    mod = _load_module()
    result = mod.schedule_next_step(
        participant_list_complete=True,
        registered_team_count=8,
        expected_team_count=8,
        has_groups=True,
        unassigned_count=0,
        too_small_groups=[],
        playoff_ready=True,
        playoff_setup_error=None,
        scheduled_total=0,
        schedule_errors=[],
        schedule_warnings=[],
        unpublished_total=0,
    )
    assert result["title"] == "Skapa spelschemat"
    assert result["state"] == "ready"


def test_quick_quality_does_not_require_expensive_score_analysis():
    mod = _load_module()
    assert mod.schedule_quick_quality(scheduled_total=12, schedule_errors=[], schedule_warnings=[])[0] == "Stabilt"
    assert mod.schedule_quick_quality(scheduled_total=12, schedule_errors=["fel"], schedule_warnings=[])[0] == "Blockerat"
    assert "schedule_score_report" not in mod.schedule_quick_quality.__code__.co_names


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"' in APP
