from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/'app.py').read_text(encoding='utf-8')
VERSION=(ROOT/'VERSION.txt').read_text(encoding='utf-8').strip()

def creation_block():
    start=APP.index('def render_new_tournament_creator')
    end=APP.index('if view_mode == "Admin":\n    st.sidebar.caption',start)
    return APP[start:end]

def test_v343_version():
    assert VERSION == '2026.09.03-414-PITCH-TIMING-MODE'
    assert f'APP_BUILD_VERSION = "{VERSION}"' in APP
    assert f'APP_VERSION = "{VERSION}"' in (ROOT/'cupnavi_core/version.py').read_text(encoding='utf-8')

def test_new_cup_defaults_to_test_environment():
    block=creation_block()
    env=block[block.index('environment_type = st.radio('):block.index('create_locale = st.selectbox(')]
    assert 'index=1' in env
    assert 'Testmiljö är standard' in block
    assert '🧪 Testmiljö · standard' in block

def test_clone_defaults_to_test_copy():
    start=APP.index('clone_environment = st.radio(')
    block=APP[start:start+500]
    assert 'index=1' in block
    assert 'Testkopia' in block

def test_creator_has_polished_guided_visual_structure():
    block=creation_block()
    for token in ['cn-create-hero','cn-create-steps','Skapa ny cup','Tävlingsklasser','Kapacitet','Regler','Namn på cup *','Skapa cup']:
        assert token in block
    assert 'Startmall · valfritt' in block
    assert '@media(max-width:640px)' in block

def test_creator_copy_is_corrected():
    block=creation_block()
    assert 'Efter Skapa guidar CupNavi' not in block
    assert 'När cupen är skapad guidar CupNavi dig vidare genom vilka som ska spela, planer/tider och lag.' in block

def test_creation_write_path_is_preserved():
    block=creation_block()
    assert 'new_tournament_id = insert_tournament_compat({' in block
    assert '"environment_type": environment_type' in block
    assert 'sync_competition_classes(new_tournament_id, [])' in block
    assert 'st.session_state["new_tournament_setup_id"] = int(new_tournament_id)' in block
