from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
R="2026.09.07-507-REVIEWED-DOCUMENT-SCHEDULE-IMPORT"
def test_environment_persisted():
    assert '"environment_type": "TEXT NOT NULL DEFAULT \'production\'"' in APP
    assert "environment_type = st.radio(" in APP
def test_test_delete_is_simple():
    assert "Radera testcup permanent" in APP
    assert "sidebar_delete_test_confirm_" in APP
def test_production_remains_deletable():
    assert "Riktiga cuper flyttas först till papperskorgen" in APP
    assert "Flytta till papperskorgen" in APP
    assert "Radera permanent" in APP
def test_clone_to_test():
    assert "clone_environment = st.radio(" in APP
    assert 'payload["environment_type"] = clone_environment' in APP
def test_test_badge():
    assert "🧪 TESTMILJÖ" in APP
def test_version():
    assert "release_ui_label(APP_BUILD_VERSION)" in APP
    assert f'APP_BUILD_VERSION = "{R}"' in APP
