from pathlib import Path

from cupnavi_core.performance import (
    PERFORMANCE_BUDGETS,
    build_performance_snapshot,
    evaluate_performance_budget,
)

VERSION = Path("VERSION.txt").read_text(encoding="utf-8").strip()
APP = Path("app.py").read_text(encoding="utf-8")


def test_v445_release_and_core_route_budgets_exist():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    for route in (
        "Turneringsvy/Info",
        "Turneringsvy/Matcher",
        "Turneringsvy/Mitt lag",
        "Admin/Adminöversikt",
        "Admin/Lag",
        "Admin/Grupper",
        "Admin/Skapa och publicera schema",
        "Admin/Kontroller",
    ):
        assert route in PERFORMANCE_BUDGETS
        assert "first_render" in PERFORMANCE_BUDGETS[route]
        assert "warm_rerun" in PERFORMANCE_BUDGETS[route]


def test_budget_evaluation_marks_db_regression():
    result = evaluate_performance_budget(
        route="Turneringsvy/Matcher",
        session_phase="warm_rerun",
        render_ms=500,
        db_calls=99,
    )
    assert result["budget_status"] == "over"
    assert "db_calls" in result["budget_over"]


def test_snapshot_exposes_budget_status_without_breaking_unbudgeted_routes():
    snap = build_performance_snapshot(
        render_ms=100,
        perf={"db_ms": 10, "db_calls": 1},
        view_mode="Turneringsvy",
        public_page="Info",
        run_seq=2,
    )
    assert snap["budget_status"] == "within"
    assert snap["budget_db_calls"] == PERFORMANCE_BUDGETS["Turneringsvy/Info"]["warm_rerun"]["db_calls"]

    other = build_performance_snapshot(
        render_ms=100,
        perf={"db_ms": 10, "db_calls": 1},
        view_mode="Unknown",
        run_seq=2,
    )
    assert other["budget_status"] == "unbudgeted"


def test_admin_diagnostics_surface_budget_status():
    assert '"Budget": (' in APP
    assert 'budget_status' in APP
    assert 'Budget för denna rutt/fas' in APP
