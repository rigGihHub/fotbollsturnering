from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E = (ROOT / "e2e/test_streamlit_critical_journey.py").read_text(encoding="utf-8")

def test_e2e_covers_core_browser_journey():
    for token in [
        'name="Admin"',
        '"Skapa ny turnering"',
        'name=re.compile(r"^Skapa testdata:")',
        "seed_completed_cup_fixture(tid)",
        '"Schema & resultat"',
        '"Tabeller"',
        '"Slutspel"',
        '"Statistik"',
        '"Cupinfo"',
        'name="Matchrapportör"',
        "public_only=1",
    ]:
        assert token in E2E

def test_e2e_fixture_requires_real_demo_data_before_seeding():
    assert "Fixture requires 2 groups/8 teams" in E2E
    assert "SELECT id,group_id FROM teams" in E2E
    assert "SELECT id FROM groups" in E2E
