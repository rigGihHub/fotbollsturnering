from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"


def test_team_page_keeps_planning_context_and_can_return_to_setup():
    block = APP[APP.index('if admin_page == "Lag":'):APP.index('if admin_page == "Grupper":')]
    assert 'Planeringsflöde · Deltagare' in block
    assert '["Grundsetup", "Lag", "Grupper", "Schema", "Kontroll", "Publicera"]' in block
    assert '← Till grundsetup' in block
    assert 'new_tournament_wizard_step_' in block
    assert '= 5' in block


def test_team_page_has_direct_review_before_write_ai_photo_import():
    block = APP[APP.index('if admin_page == "Lag":'):APP.index('if admin_page == "Grupper":')]
    assert '### ✨ Lägg in spelare från bild' in block
    assert 'st.file_uploader(' in block
    assert 'Dra hit foto eller skärmdump' in block
    assert 'extract_roster_from_image' in block
    assert 'st.data_editor(' in block
    assert 'Tröjnummer' in block and 'Födelseår' in block
    assert 'run_many(' in block
    assert 'INSERT INTO players(team_id,player_number,name,birth_year,position)' in block
