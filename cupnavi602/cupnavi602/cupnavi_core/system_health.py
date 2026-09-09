"""System-health checks that can be reused by UI, CI and a future API."""
from __future__ import annotations

def system_health(con, *, app_version, expected_schema):
    checks = {"database": False, "schema": False, "diagnostics": False}
    try:
        con.execute("SELECT 1").fetchone()
        checks["database"] = True
        row=con.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
        current=int(row[0] or 0)
        checks["schema"] = current >= int(expected_schema)
        tables={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        checks["diagnostics"] = "app_errors" in tables
    except Exception:
        current=0
    return {"ok": all(checks.values()), "version": app_version, "schema": current, "checks": checks}
