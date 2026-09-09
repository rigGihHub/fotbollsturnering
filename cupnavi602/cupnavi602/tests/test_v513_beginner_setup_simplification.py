from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
PUB=(ROOT/'cupnavi_core'/'admin_publication_view.py').read_text(encoding='utf-8')
VER=(ROOT/'cupnavi_core'/'version.py').read_text(encoding='utf-8')
def test_single_beginner_journey_exists():
    for label in ['Cupinfo','Lag','Grupper','Planer & tider','Schema','Kontroll','Publicera']:
        assert f'("{label}",' in APP
    assert 'Din väg till publicerad cup' in APP
def test_old_competing_five_step_flow_removed():
    assert '_ADMIN_FLOW_STEPS' not in APP
    assert 'Din väg till publicerad cup' in APP

def test_existing_program_is_first_run_choice():
    assert 'Läs in foto/PDF →' in APP
    assert 'args=("Import",)' in APP
def test_sidebar_has_cupinfo():
    assert '("Cupinfo", cupinfo_ready, "Cupinställningar")' in PUB
def test_version():
    assert '2026.09.07-525-OPTIONAL-REFEREE-SETUP' in VER
