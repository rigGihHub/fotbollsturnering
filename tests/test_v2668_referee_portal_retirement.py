from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_referee_route_uses_dedicated_referee_client():
    page = (ROOT / "frontend-next/src/app/referee/page.tsx").read_text()
    client = (ROOT / "frontend-next/src/components/referee-client.tsx").read_text()
    assert "RefereeClient" in page
    assert "/api/referee/session" in client
    assert "/api/referee/assignments" in client


def test_admin_exposes_referee_codes_next_to_referee_assignments():
    referee_admin = (ROOT / "frontend-next/src/components/referee-admin.tsx").read_text()
    assert "role-codes/referees" in referee_admin
    assert "NY DOMARKOD" in referee_admin
    assert "Öppna domarvy" in referee_admin


def test_referee_registry_and_assignments_remain_available():
    workspace = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text()
    repository = (ROOT / "cupnavi_api/referee_admin_repository.py").read_text()
    assert '["Domare", "#referees"]' in workspace
    assert "def assign_referee" in repository
