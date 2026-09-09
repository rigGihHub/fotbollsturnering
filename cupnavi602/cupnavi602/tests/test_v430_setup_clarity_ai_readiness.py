from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SETUP=(ROOT/'cupnavi_core'/'initial_setup_view.py').read_text()
APP=(ROOT/'app.py').read_text()
def test_duplicate_sync_control_removed():
    assert 'st.checkbox(\n            "Kräv samma avsparkstider på alla planer"' not in SETUP
    assert 'Detta val görs under Planer & tider.' in SETUP
    assert 'Ändra planer & tider' in SETUP
def test_compactness_is_human_readable():
    assert '_compact_options=["Lugnare", "Balanserad", "Ganska kompakt", "Kompakt"]' in SETUP
    assert 'Minsta lagvila ovan bryts aldrig.' in SETUP
def test_team_completion_copy_and_ai_activation():
    assert 'Komplettera laget – tröjfärger, lagansvarig m.m. (valfritt)' in APP
    assert 'AI-importen är inte aktiverad i den här miljön ännu.' in APP
