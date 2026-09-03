from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
QUALITY = (ROOT / "cupnavi_core" / "schedule_quality.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "cupnavi_core" / "schedule_template_import.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load_quality():
    spec = importlib.util.spec_from_file_location("schedule_quality_v359", ROOT / "cupnavi_core" / "schedule_quality.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_quality_profile_has_five_explainable_dimensions():
    mod = _load_quality()
    matches = [
        {"home_source":"team:1","away_source":"team:2","scheduled_start":"2026-09-01T09:00:00","pitch_number":1},
        {"home_source":"team:1","away_source":"team:3","scheduled_start":"2026-09-01T10:30:00","pitch_number":1},
        {"home_source":"team:2","away_source":"team:3","scheduled_start":"2026-09-01T12:00:00","pitch_number":1},
    ]
    result = mod.schedule_quality_dimensions(matches, min_rest_minutes=60, match_duration_minutes=30)
    assert set(result) == {"completeness","rest","flow","fairness","pitch_utilization"}
    assert result["completeness"]["score"] == 100
    assert result["rest"]["score"] == 100


def test_template_import_is_review_before_apply():
    assert "📷 Kopiera upplägg från ett tidigare schema" in VIEW
    assert "Analysera upplägget" in VIEW
    assert "Använd upplägget som utgångspunkt" in VIEW
    assert "Teamnamn ska inte kopieras" in TEMPLATE
    assert 'disabled=_analysis["confidence"] == "low"' in VIEW


def test_template_only_applies_style_not_old_teams_or_results():
    assert "synchronized_pitch_times" in VIEW
    assert "compactness_level" in VIEW
    assert "minimum_team_rest_minutes" in VIEW
    assert "recommended_group_count" in VIEW
    apply_section = VIEW[VIEW.index("Använd upplägget som utgångspunkt"):]
    assert "INSERT INTO teams" not in apply_section
    assert "home_score" not in apply_section[:2500]


def test_quality_is_loaded_only_inside_explicit_quality_view():
    assert "Kvalitetsprofil" in VIEW
    assert VIEW.index("if _show_schedule_quality:") < VIEW.index("Kvalitetsprofil")


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"' in APP
