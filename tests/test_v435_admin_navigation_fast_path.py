from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.04-449-MOBILE-PLAYOFF-ACTION"
    assert 'APP_BUILD_VERSION = "2026.09.04-449-MOBILE-PLAYOFF-ACTION"' in APP


def test_admin_cross_rerun_snapshots_exist_and_writes_invalidate():
    assert "def admin_teams_snapshot" in APP
    assert "def admin_groups_snapshot" in APP
    assert "def admin_classes_snapshot" in APP
    assert "_clear_session_read_caches()" in APP
    assert '"_cupnavi_admin_cache_"' in APP


def test_lag_page_no_longer_syncs_classes_on_every_normal_render():
    anchor = APP.index("# v435: normal navigation must be read-only")
    section = APP[anchor: anchor + 1200]
    assert "class_rows = admin_classes_snapshot(tid)" in section
    assert "if not class_rows" in section
    assert "class_rows = sync_competition_classes(tid)" in section
    assert "teams = admin_teams_snapshot(tid)" in APP
