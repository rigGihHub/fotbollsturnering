from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_next_reporting_supports_penalty_decisions_and_dependency_refresh():
    source = (ROOT / "frontend-next/src/components/publish-reporting-admin.tsx").read_text(encoding="utf-8")
    assert "home_penalties" in source
    assert "away_penalties" in source
    assert "Hemmastraffar" in source
    assert "Bortastraffar" in source
    assert "awaiting_decision" in source
    assert "await load()" in source
    assert "Nästa match får deltagarna automatiskt från slutspelsträdet" in source


def test_reporting_route_keeps_optimistic_penalty_expectations():
    source = (ROOT / "cupnavi_api/publish_reporting_routes.py").read_text(encoding="utf-8")
    assert "expected_home_penalties" in source
    assert "expected_away_penalties" in source
    assert "home_penalties=payload.home_penalties" in source
