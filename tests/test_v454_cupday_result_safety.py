from pathlib import Path

APP = Path('app.py').read_text()
VIEW = Path('cupnavi_core/schedule_workspace_view.py').read_text()
VERSION = Path('VERSION.txt').read_text().strip()


def test_v454_version():
    assert VERSION == '2026.09.07-505-ADMIN-PREVIEW-CODES-SETTINGS'


def test_schedule_score_write_has_stale_snapshot_protection():
    block = APP[APP.index('def _save_bulk_schedule_results'):APP.index('if admin_page == "Skapa och publicera schema"')]
    assert 'expected_home' in block and 'expected_away' in block
    assert 'home_score IS ? AND away_score IS ?' in block
    assert 'conflicts.append' in block


def test_schedule_score_write_uses_event_integrity_guard():
    block = APP[APP.index('def _save_bulk_schedule_results'):APP.index('if admin_page == "Skapa och publicera schema"')]
    assert '_result_event_integrity(con, match_row, home_score, away_score)' in block
    assert 'integrity_blocked' in block


def test_schedule_editor_passes_rendered_score_snapshot_and_surfaces_failures():
    assert 'changed_scores.append((home_score, away_score, match_id, expected_home, expected_away))' in VIEW
    assert 'hade ändrats efter att schemat laddades och skrevs inte över' in VIEW
    assert 'redan registrerade målskyttsmål' in VIEW
