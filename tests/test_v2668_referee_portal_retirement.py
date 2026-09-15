from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_referee_route_preserves_cup_and_redirects_to_reporter():
    page = (ROOT / "frontend-next/src/app/referee/page.tsx").read_text()
    assert 'redirect(cup?`/reporter?cup=${encodeURIComponent(cup)}`:"/reporter")' in page


def test_admin_exposes_one_reporting_login_model():
    operations = (ROOT / "frontend-next/src/components/admin-operations.tsx").read_text()
    assert "RefereeRoleCodeAdmin" not in operations
    assert "En gemensam rapportörskod för resultat" in operations


def test_referee_registry_and_assignments_remain_available():
    workspace = (ROOT / "frontend-next/src/components/admin-workspace.tsx").read_text()
    repository = (ROOT / "cupnavi_api/referee_admin_repository.py").read_text()
    assert '["Domare", "#referees"]' in workspace
    assert "def assign_referee" in repository
