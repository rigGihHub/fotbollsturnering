from pathlib import Path
import importlib.util
import sys

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
TEMPLATE = (ROOT / "cupnavi_core" / "schedule_template_import.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")


def _load_template():
    spec = importlib.util.spec_from_file_location("schedule_template_import_v360", ROOT / "cupnavi_core" / "schedule_template_import.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_adapts_old_structure_to_current_team_and_pitch_count():
    mod = _load_template()
    old = {
        "confidence": "high",
        "summary": "Två grupper med fyra lag.",
        "group_count": 2,
        "typical_group_size": 4,
        "pitch_count": 2,
        "synchronized_pitch_times": True,
        "first_match_time": "09:00",
        "last_match_time": "14:00",
        "estimated_match_interval_minutes": 30,
        "estimated_min_team_rest_minutes": 60,
        "compactness": 70,
        "playoff_present": True,
        "caveats": [],
    }
    adapted = mod.adapt_schedule_template(
        old,
        team_count=12,
        pitch_count=3,
        current_match_duration_minutes=25,
        current_min_rest_minutes=45,
    )
    assert adapted["team_count"] == 12
    assert adapted["pitch_count"] == 3
    assert adapted["group_count"] == 3
    assert adapted["group_sizes"] == [4, 4, 4]
    assert adapted["synchronized_pitch_times"] is True
    assert adapted["minimum_team_rest_minutes"] == 60


def test_preview_is_shown_before_apply():
    assert "Så skulle upplägget se ut i den här cupen" in VIEW
    assert "Likhet med originalupplägget" in VIEW
    assert "Använd det anpassade upplägget" in VIEW
    assert VIEW.index("Så skulle upplägget se ut i den här cupen") < VIEW.index("Använd det anpassade upplägget")


def test_current_pitch_count_is_not_overwritten_from_old_image():
    apply_section = VIEW[VIEW.index("Använd det anpassade upplägget"):]
    assert "pitch_count=?" not in apply_section[:3500]
    assert 'pitch_count=max(1, int(rules["pitch_count"] or 1))' in VIEW


def test_version():
    assert 'APP_BUILD_VERSION = "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"' in APP
