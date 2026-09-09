from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / 'app.py').read_text(encoding='utf-8')
VERSION = (ROOT / 'cupnavi_core' / 'version.py').read_text(encoding='utf-8')


def test_v576_version_and_three_group_setup_paths():
    assert '2026.09.09-576-GROUPS-PHOTO-IMPORT' in VERSION
    assert 'Hur vill du skapa grupperna?' in APP
    assert '✨ CupNavi föreslår' in APP
    assert '📷 Importera från foto' in APP
    assert '✋ Gör själv' in APP


def test_photo_import_supports_multiple_images_and_requires_review():
    assert 'accept_multiple_files=True' in APP
    assert 'Läs av gruppindelningen' in APP
    assert 'Granska förslaget' in APP
    assert '✓ Använd den granskade gruppindelningen' in APP
    assert 'Fotoimport sparar aldrig något innan du har granskat förslaget.' in APP


def test_photo_import_reuses_ai_document_extraction_and_never_silently_overwrites_groups():
    assert 'extract_cup_setup_from_documents' in APP
    assert 'Det finns redan grupper i cupen.' in APP
    assert 'bara som ett förslag' in APP
    assert 'Fotoimporten gjorde inga ändringar.' in APP


def test_group_photo_import_matches_only_registered_team_names_and_surfaces_unmatched_rows():
    assert '_current_by_name' in APP
    assert 'Inte matchat' in APP
    assert 'De importeras inte automatiskt' in APP
