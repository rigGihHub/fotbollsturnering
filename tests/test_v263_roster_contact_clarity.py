from pathlib import Path

APP = (Path(__file__).parents[1] / "app.py").read_text(encoding="utf-8")
VERSION = (Path(__file__).parents[1] / "VERSION.txt").read_text(encoding="utf-8").strip()

def test_v263_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"

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
    assert 'if st.toggle("Fler lagverktyg", value=False, key=f"lazy_team_tools_{tid}"' in APP
    assert "Valfria verktyg. De behövs inte för att slutföra den vanliga lagregistreringen." in APP
