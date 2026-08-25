from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "2026.08.25-192-CI-HEALTH-DEPENDENCY"


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
    assert 'st.sidebar.caption("Version v.1.192")' in app
