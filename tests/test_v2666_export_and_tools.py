from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pdf_download_validates_signature_and_delays_revoke():
    source = (ROOT / "frontend-next/src/components/export-admin.tsx").read_text()
    assert 'signature!=="%PDF-"' in source
    assert 'new Blob([bytes],{type:"application/pdf"})' in source
    assert 'window.setTimeout(()=>URL.revokeObjectURL(url),60_000)' in source


def test_export_queries_do_not_require_optional_schema_columns():
    source = (ROOT / "cupnavi_api/export_repository.py").read_text()
    assert 'SELECT * FROM matches WHERE tournament_id=?' in source
    assert 'SELECT * FROM pitches WHERE tournament_id=?' in source
    assert 'SELECT pitch_number,name,address FROM pitches' not in source


def test_referee_and_import_views_have_dedicated_layouts():
    referee = (ROOT / "frontend-next/src/components/referee-admin.tsx").read_text()
    importer = (ROOT / "frontend-next/src/components/import-admin.tsx").read_text()
    css = (ROOT / "frontend-next/src/app/admin-tools-v2666.css").read_text()
    assert 'referee-assignment-list' in referee
    assert 'home_team' in referee and 'away_team' in referee
    assert 'import-file-picker' in importer
    assert 'html[data-admin-step="referees"]' in css
    assert 'html[data-admin-step="import"]' in css
