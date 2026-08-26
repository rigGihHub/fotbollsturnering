from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
CONFIG=(ROOT/".streamlit/config.toml").read_text(encoding="utf-8")
R="2026.08.26-193-FULL-UI-UX-REDESIGN"

def test_fingerprint_runs_before_core_imports():
    fingerprint=APP.index("ACTIVE_SOURCE_FINGERPRINT, SOURCE_PACKAGE_REFRESHED")
    core_import=APP.index("from cupnavi_core.version import APP_VERSION")
    assert fingerprint < core_import

def test_package_cache_is_invalidated_on_source_change():
    assert "def _refresh_cupnavi_imports_if_sources_changed" in APP
    assert 'module_name.startswith("cupnavi_core.")' in APP
    assert "sys.modules.pop(module_name, None)" in APP
    assert "importlib.invalidate_caches()" in APP

def test_source_fingerprint_covers_core_files():
    assert 'core_root.rglob("*.py")' in APP
    assert 'root / "app.py"' in APP
    assert 'root / "requirements.txt"' in APP

def test_streamlit_uses_poll_file_watcher():
    assert 'fileWatcherType = "poll"' in CONFIG
    assert "runOnSave = true" in CONFIG

def test_admin_has_deploy_diagnostics():
    assert "Teknisk release-status" in APP
    assert "Deploy-fingerprint" in APP
    assert "Automatiska kodomladdningar" in APP

def test_release_sync():
    assert f'APP_BUILD_VERSION = "{R}"' in APP
    assert f'APP_VERSION = "{R}"' in (ROOT/"cupnavi_core/version.py").read_text(encoding="utf-8")
    assert (ROOT/"VERSION.txt").read_text().strip()==R
