from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
VERSION=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()

def test_release_version():
    assert VERSION == '2026.08.31-353-GROUP-FLOW-PITCH-TIMING'

def test_mobile_creation_not_sidebar_only():
    assert 'def render_new_tournament_creator' in APP
    assert 'with st.expander("➕ Skapa ny turnering", expanded=True)' in APP
    assert 'with st.expander("➕ Ny turnering", expanded=False)' in APP
    assert 'render_new_tournament_creator(key_prefix="mobile_empty")' in APP
    assert 'render_new_tournament_creator(key_prefix="mobile_main")' in APP

def test_smart_group_preview_and_explicit_commit():
    assert 'def _smart_group_plan' in APP
    assert 'Smart gruppindelning' in APP
    assert 'Skapa föreslagen gruppindelning' in APP
    assert 'fresh_team_state != expected_team_state' in APP
    assert 'Inga automatiska ändringar gjordes' in APP or 'inga grupper skapades' in APP.lower()
