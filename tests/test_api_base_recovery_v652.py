from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend-next/src"


def test_client_api_base_rejects_placeholder_and_relative_values():
    helper = (FRONTEND / "lib/client-api.ts").read_text(encoding="utf-8")
    assert "configured && /^https?:\\/\\//i.test(configured)" in helper
    assert '"https://cupnavi-api.onrender.com"' in helper
    assert '"http://localhost:8000"' in helper


def test_every_admin_client_uses_the_validated_api_base():
    components = [
        "admin-workspace.tsx", "admin-operations.tsx", "rules-admin.tsx",
        "schedule-admin.tsx", "venue-admin.tsx", "referee-admin.tsx",
        "playoff-admin.tsx", "import-admin.tsx", "publish-reporting-admin.tsx",
    ]
    for name in components:
        source = (FRONTEND / "components" / name).read_text(encoding="utf-8")
        assert 'from "../lib/client-api"' in source, name
        assert "process.env.NEXT_PUBLIC_CUPNAVI_API_BASE" not in source, name


def test_v652_release_is_synchronized():
    version = "2026.09.12-652-API-BASE-RECOVERY"
    assert (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip() == version
    assert f'APP_VERSION = "{version}"' in (ROOT / "cupnavi_core/version.py").read_text(encoding="utf-8")
