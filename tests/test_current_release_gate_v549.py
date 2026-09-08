from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = "2026.09.08-549-CURRENT-RELEASE-GATE"


def test_current_release_version_is_synchronized():
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert version == EXPECTED
    assert f'APP_BUILD_VERSION = "{EXPECTED}"' in app
    assert f'APP_VERSION = "{EXPECTED}"' in core


def test_public_weather_is_intentionally_opt_in_for_first_paint_performance():
    view = (ROOT / "cupnavi_core" / "public_match_filters_view.py").read_text(encoding="utf-8")
    anchor = '"🌦️ " + tr("Visa väderprognos")'
    start = view.index(anchor)
    weather_toggle = view[start:start + 350]
    assert "value=False" in weather_toggle
    assert "first paint" in view


def test_current_reporter_resilience_contract_is_present():
    reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
    assert "Sparar" in reporter
    assert "Sparat" in reporter
    assert "Dåligt nät" in reporter
    assert "Försök igen" in reporter or "Läs om" in reporter
    assert "15" in reporter


def test_current_reporter_setup_gates_remain_present():
    reporter = (ROOT / "cupnavi_core" / "match_reporter_workspace_view.py").read_text(encoding="utf-8")
    # These settings must still drive optional player-event controls.
    for token in ("_setup_scorers", "_setup_assists", "_setup_cards"):
        assert token in reporter
