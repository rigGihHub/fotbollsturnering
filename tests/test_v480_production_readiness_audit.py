from pathlib import Path
from cupnavi_core.go_live_readiness import build_go_live_readiness

VERSION = "2026.09.07-500-MULTI-DOCUMENT-IMPORT"
APP = Path("app.py").read_text(encoding="utf-8")


def _base(**overrides):
    kwargs = dict(
        cloud_database_enabled=True,
        database_config_partial=False,
        admin_access_configured=True,
        production_environment=True,
        schema_version=32,
        required_schema_version=32,
        missing_tables=[],
        published=True,
        schedule_dirty=False,
        schedule_errors=[],
        stats={
            "reporter_codes": 1,
            "teams": 4,
            "matches": 6,
            "unscheduled_matches": 0,
            "unpublished_matches": 0,
            "players": 20,
            "teams_without_players": 0,
            "testable_matches": 4,
        },
    )
    kwargs.update(overrides)
    return kwargs


def test_version_is_v480():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_partial_turso_config_is_blocker():
    readiness = build_go_live_readiness(**_base(
        cloud_database_enabled=False,
        database_config_partial=True,
    ))
    database = next(item for item in readiness.items if item.key == "database")
    assert database.state == "blocker"
    assert "delvis konfigurerat" in database.detail


def test_missing_admin_password_is_blocker():
    readiness = build_go_live_readiness(**_base(admin_access_configured=False))
    admin = next(item for item in readiness.items if item.key == "admin_access")
    assert admin.state == "blocker"
    assert "ADMIN_PASSWORD" in admin.detail


def test_complete_cloud_and_admin_config_are_ok():
    readiness = build_go_live_readiness(**_base())
    assert readiness.ready is True
    states = {item.key: item.state for item in readiness.items}
    assert states["database"] == "ok"
    assert states["admin_access"] == "ok"


def test_db_refuses_partial_turso_fallback():
    start = APP.index("def db():")
    end = APP.index("def _playoff_dependency_guard(", start)
    block = APP[start:end]
    assert "if TURSO_CONFIG_PARTIAL:" in block
    assert "vägrar använda lokal fallback" in block
    assert "sqlite3.connect(DB_FILE)" in block


def test_partial_flag_requires_exactly_one_turso_secret():
    assert "TURSO_CONFIG_PARTIAL = bool(TURSO_DATABASE_URL) != bool(TURSO_AUTH_TOKEN)" in APP


def test_go_live_receives_production_config_state():
    assert "database_config_partial=TURSO_CONFIG_PARTIAL" in APP
    assert "admin_access_configured=ADMIN_ACCESS_CONFIGURED" in APP


def test_weather_and_routes_remain_nonfatal_optional_services():
    assert 'return {}, "Väderprognosen kan inte hämtas just nu."' in APP
    assert "CupNavi kunde inte beräkna restiden mellan" in APP
