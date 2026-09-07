from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEW = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "cupnavi_core" / "version.py").read_text(encoding="utf-8")

def test_v510_version():
    assert "2026.09.07-520-UNIQUE-PUBLICATION-CHECKLIST-KEYS" in VERSION

def test_existing_schedule_has_visible_manual_edit_path():
    assert "Redigera befintligt schema manuellt" in VIEW
    assert "Öppna manuell schemaredigering" in VIEW
    assert "Övriga matcher lämnades orörda" in VIEW

def test_manual_edit_protects_played_matches_and_unpublishes_changed_match():
    assert "home_score IS NULL AND away_score IS NULL" in VIEW
    assert "schedule_published=0" in VIEW
    assert "Spelade matcher kan inte ändras här" in VIEW

def test_group_match_opponents_can_be_corrected_safely():
    assert '"Hemma"' in VIEW
    assert '"Borta"' in VIEW
    assert "Samma lag kan inte möta sig självt" in VIEW
