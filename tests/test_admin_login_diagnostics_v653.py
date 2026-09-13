from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text(encoding="utf-8")


def test_login_checks_real_api_health_with_timeout():
    assert 'fetch(`${API_BASE}/health`' in WORKSPACE
    assert 'controller.abort(),8000' in WORKSPACE
    assert 'setApiStatus("online")' in WORKSPACE
    assert 'setApiStatus("offline")' in WORKSPACE


def test_login_distinguishes_auth_rate_limit_and_configuration_errors():
    assert 'response.status === 401' in WORKSPACE
    assert 'response.status === 429' in WORKSPACE
    assert 'response.status === 503' in WORKSPACE
    assert "Fel e-postadress eller lösenord." in WORKSPACE
    assert "För många försök." in WORKSPACE


def test_password_help_does_not_claim_secrets_can_be_recovered():
    assert "Glömt lösenordet?" in WORKSPACE
    assert "Lösenord kan inte visas eller hämtas ur CupNavi." in WORKSPACE
    assert "CUPNAVI_OWNER_PASSWORD" not in WORKSPACE


def test_offline_api_blocks_pointless_login_submission():
    assert 'disabled={busy||apiStatus==="offline"}' in WORKSPACE
    assert 'role={error?"alert":undefined}' in WORKSPACE


def test_v653_release_is_synchronized():
    version = "2026.09.12-653-ADMIN-LOGIN-DIAGNOSTICS"
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == version
    version_module = (ROOT / "cupnavi_core/version.py").read_text(encoding="utf-8")
    assert f'APP_VERSION = "{version}"' in version_module
