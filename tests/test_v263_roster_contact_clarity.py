from pathlib import Path

APP = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
VERSION = (Path(__file__).parents[1] / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_v263_version():
    assert VERSION == "2026.08.31-342-POST-SIMPLIFICATION-AUDIT"

def test_team_contact_fields_identify_team_responsible():
    assert "Lagansvarig kontaktperson" in APP
    assert 'text_input("Namn på lagansvarig"' in APP
    assert 'text_input("Telefon till lagansvarig"' in APP
    assert 'text_input("E-post till lagansvarig"' in APP

def test_roster_navigation_is_clear_but_route_stays_compatible():
    assert 'if admin_page == "Trupper"' in APP
    assert 'if admin_page == "Trupper":' in APP
    assert 'st.header("Spelare & trupper")' in APP
    assert "Välj lag och hantera spelare manuellt eller via AI-import." in APP
    assert "Spelare och trupper hanteras via **Fler lagverktyg** ovan." in APP
