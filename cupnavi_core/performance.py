"""Lightweight performance observability helpers.

The helpers are intentionally framework-agnostic. CupNavi can record one compact
snapshot per Streamlit rerun without introducing external analytics or long-lived
caches. Structured log output is opt-in through CUPNAVI_PERF_LOG=1.

v445 adds route-specific soft budgets. They are deliberately diagnostic rather
than hard runtime limits: a slow network must never break a cup. The budgets make
regressions visible and give every high-traffic route an explicit target for DB
roundtrips and render latency.
"""
from __future__ import annotations

import json
from typing import Any, Mapping


# Soft performance budgets for the routes that matter most on cup day.
# ``first_render`` is allowed more work than a warm interaction rerun. Budgets
# are evaluated in diagnostics/logs and are also pinned by the CI performance
# contract so future features cannot silently remove the targets.
PERFORMANCE_BUDGETS: dict[str, dict[str, dict[str, float | int]]] = {
    "Turneringsvy/Info": {
        "first_render": {"render_ms": 1800.0, "db_calls": 5},
        "warm_rerun": {"render_ms": 900.0, "db_calls": 2},
    },
    "Turneringsvy/Matcher": {
        "first_render": {"render_ms": 2200.0, "db_calls": 7},
        "warm_rerun": {"render_ms": 1100.0, "db_calls": 3},
    },
    "Turneringsvy/Mitt lag": {
        "first_render": {"render_ms": 2000.0, "db_calls": 6},
        "warm_rerun": {"render_ms": 1000.0, "db_calls": 3},
    },
    "Admin/Adminöversikt": {
        "first_render": {"render_ms": 2500.0, "db_calls": 10},
        "warm_rerun": {"render_ms": 1200.0, "db_calls": 4},
    },
    "Admin/Lag": {
        "first_render": {"render_ms": 2200.0, "db_calls": 8},
        "warm_rerun": {"render_ms": 1100.0, "db_calls": 4},
    },
    "Admin/Grupper": {
        "first_render": {"render_ms": 2200.0, "db_calls": 8},
        "warm_rerun": {"render_ms": 1100.0, "db_calls": 4},
    },
    "Admin/Skapa och publicera schema": {
        "first_render": {"render_ms": 3000.0, "db_calls": 12},
        "warm_rerun": {"render_ms": 1500.0, "db_calls": 6},
    },
    "Admin/Kontroller": {
        "first_render": {"render_ms": 3000.0, "db_calls": 12},
        "warm_rerun": {"render_ms": 1500.0, "db_calls": 6},
    },
}


def performance_budget_for_route(route: str, session_phase: str) -> dict[str, float | int] | None:
    """Return a copy of the soft budget for a route/phase, if one is defined."""
    route_budget = PERFORMANCE_BUDGETS.get(str(route or ""))
    if not route_budget:
        return None
    phase_budget = route_budget.get(str(session_phase or ""))
    return dict(phase_budget) if phase_budget else None


def evaluate_performance_budget(
    *,
    route: str,
    session_phase: str,
    render_ms: float,
    db_calls: int,
) -> dict[str, Any]:
    """Evaluate one rerun against its route budget without affecting execution."""
    budget = performance_budget_for_route(route, session_phase)
    if budget is None:
        return {
            "budget_status": "unbudgeted",
            "budget_render_ms": None,
            "budget_db_calls": None,
            "budget_over": [],
        }

    over: list[str] = []
    if float(render_ms or 0.0) > float(budget["render_ms"]):
        over.append("render_ms")
    if int(db_calls or 0) > int(budget["db_calls"]):
        over.append("db_calls")
    return {
        "budget_status": "over" if over else "within",
        "budget_render_ms": float(budget["render_ms"]),
        "budget_db_calls": int(budget["db_calls"]),
        "budget_over": over,
    }


def build_performance_snapshot(*, render_ms: float, perf: Mapping[str, Any], view_mode: str,
                               admin_page: str | None = None, public_page: str | None = None,
                               run_seq: int = 1, source_refreshed: bool = False) -> dict[str, Any]:
    db_ms = round(float(perf.get("db_ms", 0.0) or 0.0), 1)
    render_ms = round(float(render_ms or 0.0), 1)
    db_calls = int(perf.get("db_calls", 0) or 0)
    writes = int(perf.get("writes", 0) or 0)
    cache_hits = int(perf.get("cache_hits", 0) or 0)
    derived_hits = int(perf.get("derived_hits", 0) or 0)
    db_share = round((db_ms / render_ms) * 100, 1) if render_ms > 0 else 0.0

    route = str(view_mode or "unknown")
    if route == "Admin" and admin_page:
        route = f"Admin/{admin_page}"
    elif route == "Turneringsvy" and public_page:
        route = f"Turneringsvy/{public_page}"

    run_seq = max(1, int(run_seq or 1))
    session_phase = "first_render" if run_seq <= 1 else "warm_rerun"
    budget_result = evaluate_performance_budget(
        route=route,
        session_phase=session_phase,
        render_ms=render_ms,
        db_calls=db_calls,
    )

    return {
        "route": route,
        "render_ms": render_ms,
        "db_ms": db_ms,
        "db_calls": db_calls,
        "writes": writes,
        "query_cache_hits": cache_hits,
        "derived_cache_hits": derived_hits,
        "db_share_pct": db_share,
        "run_seq": run_seq,
        "session_phase": session_phase,
        "source_refreshed": bool(source_refreshed),
        **budget_result,
    }


def performance_log_line(snapshot: Mapping[str, Any]) -> str:
    """Stable one-line JSON for Streamlit/Cloud logs."""
    return "CUPNAVI_PERF " + json.dumps(dict(snapshot), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
