from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
FLOW = (ROOT / 'cupnavi_core' / 'planning_flow_nav.py').read_text(encoding='utf-8')
OVERVIEW = (ROOT / 'cupnavi_core' / 'admin_overview.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'VERSION.txt').read_text(encoding='utf-8').strip()


def test_v566_version():
    assert VERSION == '2026.09.08-566-PLANNING-PITCHES-NOVICE-UX'


def test_planning_has_dedicated_route():
    assert '("Planer & tider", "Planer & tider")' in APP
    assert '"Planer & tider": "Planer & tider"' in FLOW
    assert 'elif admin_page == "Planer & tider":' in APP


def test_novice_required_optional_hierarchy():
    assert 'Det här måste vara klart' in APP
    assert 'Valfritt: adresser och restid mellan planer' in APP
    assert 'Adresser och restider är frivilliga' in APP
    assert 'Obligatoriska planuppgifter är klara' in APP


def test_schedule_dirty_when_capacity_or_windows_change():
    block = APP.split('elif admin_page == "Planer & tider":',1)[1].split('elif admin_page == "Adminöversikt":',1)[0]
    assert block.count('UPDATE tournaments SET schedule_dirty=CASE WHEN EXISTS') >= 3


def test_admin_overview_routes_missing_pitches_to_dedicated_page():
    assert '("Planer & tider", "Minst en spelplan med tillgängliga tider behövs.", "Planer & tider")' in OVERVIEW


def test_domare_remains_optional_next_step():
    assert 'Domare är nästa steg men är frivilligt' in APP
    assert 'Fortsätt till Domare →' in APP
