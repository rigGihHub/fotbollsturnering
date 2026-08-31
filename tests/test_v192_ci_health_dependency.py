from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026.08.31-351-SETUP-COMPLETION-HANDOFF"


def test_health_contract_testclient_dependency_is_declared():
    dev = (ROOT / "requirements-dev.txt").read_text(encoding="utf-8").lower()
    assert "httpx>=" in dev
    script = (ROOT / "scripts" / "check_health_contract.py").read_text(encoding="utf-8")
    assert "from fastapi.testclient import TestClient" in script


def test_v192_release_sync_and_visible_version():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    core = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == RELEASE
    assert f'APP_BUILD_VERSION = "{RELEASE}"' in app
    assert f'APP_VERSION = "{RELEASE}"' in core
    assert 'st.sidebar.caption(release_ui_label(APP_BUILD_VERSION))' in app


def test_release_manifest_excludes_runtime_and_secret_files():
    script=(ROOT/"scripts"/"generate_release_manifest.py").read_text(encoding="utf-8")
    assert '".db"' in script
    assert '".sqlite"' in script
    assert '"backups"' in script
    assert 'path.name == ".env"' in script
    assert '.streamlit/secrets.toml' in script
    manifest=(ROOT/"RELEASE_MANIFEST.txt").read_text(encoding="utf-8")
    forbidden=("./turnering.db", ".db-shm", ".db-wal", "./.env", "/backups/")
    assert not any(token in manifest for token in forbidden)
