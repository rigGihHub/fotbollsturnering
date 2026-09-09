from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_publicera_is_real_seventh_step():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    nav = (ROOT / "cupnavi_core" / "planning_flow_nav.py").read_text(encoding="utf-8")
    assert 'Steg 7 av 7' in app
    assert 'Fortsätt till Publicera →' in app
    assert 'planning_control_focus_' in nav
    assert 'current_step="Publicera"' in app

def test_publish_action_not_buried_in_control():
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    assert 'keep the irreversible action out of Kontroll' in app
    assert 'Cupen kan inte publiceras ännu' in app
    assert 'Allt obligatoriskt är klart' in app

def test_version():
    assert (ROOT / "VERSION.txt").read_text().strip() == "2026.09.07-525-OPTIONAL-REFEREE-SETUP"
