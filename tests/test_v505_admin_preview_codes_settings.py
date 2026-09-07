from pathlib import Path

APP = Path('app.py').read_text(encoding='utf-8')
SETUP = Path('cupnavi_core/initial_setup_view.py').read_text(encoding='utf-8')
PREVIEW = Path('cupnavi_core/admin_publish_preview.py').read_text(encoding='utf-8')


def test_admin_sidebar_keeps_codes_one_click_away():
    assert '"Öppna alla koder"' in APP
    assert '"Åtkomst & koder"' in APP
    assert 'Matchrapportör · domare · lag' in APP


def test_publication_has_meaningful_preview_before_publish_controls():
    preview_call = APP.index('render_publish_preview(')
    publish_call = APP.index('render_admin_publication_controls(', preview_call)
    assert preview_call < publish_call
    assert 'Förhandsgranska före publicering' in PREVIEW
    assert 'Lag och grupper' in PREVIEW
    assert 'Schema' in PREVIEW
    assert 'Planer och platser' in PREVIEW
    assert 'Slutspel' in PREVIEW
    assert 'Förhandsgranskningen ändrar ingenting' in PREVIEW


def test_existing_settings_editor_uses_light_surface_and_edit_copy():
    assert '_editing_existing' in SETUP
    assert 'background:#f6f8f7!important' in SETUP
    assert 'Ändra cupinställningar' in SETUP
    assert 'Inställningar för ' in SETUP
    assert 'CupNavi visar konsekvenser innan större ändringar' in SETUP


def test_v505_version_is_synchronized():
    version='2026.09.07-520-UNIQUE-PUBLICATION-CHECKLIST-KEYS'
    assert version in APP
    assert version in Path('cupnavi_core/version.py').read_text(encoding='utf-8')
    assert Path('VERSION.txt').read_text(encoding='utf-8').strip() == version
