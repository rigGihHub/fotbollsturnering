"""Lightweight performance observability helpers.

The helpers are intentionally framework-agnostic. CupNavi can record one compact
snapshot per Streamlit rerun without introducing external analytics or long-lived
caches. Structured log output is opt-in through CUPNAVI_PERF_LOG=1.
"""
from __future__ import annotations

import json
from typing import Any, Mapping


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

    return {
        "route": route,
        "render_ms": render_ms,
        "db_ms": db_ms,
        "db_calls": db_calls,
        "writes": writes,
        "query_cache_hits": cache_hits,
        "derived_cache_hits": derived_hits,
        "db_share_pct": db_share,
        "run_seq": max(1, int(run_seq or 1)),
        "session_phase": "first_render" if int(run_seq or 1) <= 1 else "warm_rerun",
        "source_refreshed": bool(source_refreshed),
    }


def performance_log_line(snapshot: Mapping[str, Any]) -> str:
    """Stable one-line JSON for Streamlit/Cloud logs."""
    return "CUPNAVI_PERF " + json.dumps(dict(snapshot), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
