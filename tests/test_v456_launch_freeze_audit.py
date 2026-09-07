from pathlib import Path

from cupnavi_core.go_live_readiness import build_go_live_readiness

VERSION = "2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS"
APP = Path("app.py").read_text(encoding="utf-8")
ROLE_VIEW = Path("cupnavi_core/admin_role_codes_view.py").read_text(encoding="utf-8")


def _stats(**overrides):
    data = {
        "teams": 8,
        "players": 80,
        "teams_without_players": 0,
        "matches": 16,
        "unscheduled_matches": 0,
        "unpublished_matches": 0,
        "testable_matches": 12,
        "reporter_codes": 1,
    }
    data.update(overrides)
    return data


def _build(*, production_environment=True, cloud=True):
    return build_go_live_readiness(
        cloud_database_enabled=cloud,
        production_environment=production_environment,
        schema_version=32,
        required_schema_version=32,
        missing_tables=[],
        published=True,
        schedule_dirty=False,
        schedule_errors=[],
        stats=_stats(),
    )


def test_version_is_v456():
    assert VERSION in APP
    assert Path("VERSION.txt").read_text().strip() == VERSION


def test_test_environment_is_a_go_live_blocker():
    readiness = _build(production_environment=False)
    blocker = next(item for item in readiness.blockers if item.key == "environment")
    assert "Testmiljö" in blocker.detail
    assert readiness.ready is False


def test_real_cup_environment_is_green():
    readiness = _build(production_environment=True)
    item = next(item for item in readiness.items if item.key == "environment")
    assert item.state == "ok"
    assert "Riktig cup" in item.detail


def test_local_database_remains_a_go_live_blocker():
    readiness = _build(cloud=False)
    assert any(item.key == "database" for item in readiness.blockers)


def test_admin_go_live_passes_actual_tournament_environment():
    assert "production_environment=not is_test_environment(tournament)" in APP


def test_demo_tools_remain_guarded_to_test_environment():
    assert "_demo_environment_allowed = is_test_environment(tournament)" in APP
    assert "Testverktygen är avstängda i riktiga cuper." in APP


def test_role_codes_are_random_and_not_hardcoded_defaults():
    assert "generate_short_numeric_code(4)" in APP
    assert "Kopiera eller dela koden nu. Den visas bara efter generering." in ROLE_VIEW


def test_local_sqlite_is_explicit_and_go_live_gate_requires_turso():
    assert "if CLOUD_DATABASE_ENABLED:" in APP
    assert "return CloudConnection(_cloud_raw_connection())" in APP
    assert "con = sqlite3.connect(DB_FILE)" in APP
