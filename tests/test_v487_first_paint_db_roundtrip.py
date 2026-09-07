from pathlib import Path

VERSION = "2026.09.07-510-MANUAL-IMPORTED-SCHEDULE-EDIT"
APP = Path("app.py").read_text(encoding="utf-8")


def test_version_is_v487():
    assert Path("VERSION.txt").read_text().strip() == VERSION
    assert VERSION in APP


def test_public_empty_projection_skips_db_connection():
    assert "if not include_matches and not include_teams:" in APP
    assert 'return {"matches": [], "teams": []}' in APP


def test_cupday_has_batched_boot_snapshot():
    assert "def cupday_boot_db_snapshot" in APP
    assert 'return {"rules": rules, "matches": matches, "checkins": checkins}' in APP


def test_cupday_uses_boot_snapshot():
    assert "_day_boot = cupday_boot_db_snapshot" in APP
    assert '_day_rules = _day_boot["rules"]' in APP
    assert '_day_matches = [dict(row) for row in _day_boot["matches"]]' in APP
    assert 'for row in _day_boot["checkins"]' in APP


def test_old_cupday_rule_roundtrip_is_removed():
    assert '_day_rules = one_row("SELECT * FROM schedule_rules WHERE tournament_id=?"' not in APP


def test_no_schema_change():
    migrations = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = 32" in migrations
