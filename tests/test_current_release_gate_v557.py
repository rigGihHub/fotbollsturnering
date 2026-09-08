from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
WIZARD = (ROOT / "cupnavi_core" / "new_tournament_wizard.py").read_text(encoding="utf-8")
CREATOR = (ROOT / "cupnavi_core" / "cup_document_creator_view.py").read_text(encoding="utf-8")
SCHEDULE = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
VERSION = "2026.09.08-557-PHOTO-SCHEDULE-PERSISTENCE"


def test_release_files_are_current():
    assert VERSION in APP
    assert (ROOT / "VERSION.txt").read_text().strip() == VERSION
    assert VERSION in (ROOT / "cupnavi_core" / "version.py").read_text()


def test_synchronized_pitch_times_remain_the_new_cup_default():
    assert "synchronized_pitch_times INTEGER NOT NULL DEFAULT 1" in APP
    assert "ALTER TABLE schedule_rules ADD COLUMN synchronized_pitch_times INTEGER NOT NULL DEFAULT 1" in APP
    assert "VALUES(?,?,?,?,?,1)" in APP


def test_pitch_addresses_only_block_when_address_planning_is_enabled():
    assert '_address_planning_enabled = bool(_row_value(rules, "consider_pitch_travel", 0))' in WIZARD
    assert 'address_ok = (not _address_planning_enabled) or _filled_addresses_verified' in WIZARD
    assert '(not consider_travel) or not bool(_addresses_to_verify)' in SETUP
    assert '(not consider_travel or not _addresses_to_verify)' in SETUP


def test_period_break_copy_and_visibility_are_retained():
    assert "Paus mellan halvlekar/perioder" in APP
    assert "Paus mellan halvlekar/perioder" in SETUP
    assert "if int(edited_halves) >= 2:" in APP
    assert "if int(halves) >= 2:" in APP
    assert "if int(_setup_halves_value) >= 2:" in SETUP


def test_reviewed_photo_schedule_is_selected_by_default_and_persists():
    assert '"Använd det granskade matchprogrammet som cupens schema", value=True' in CREATOR
    assert "blir det cupens befintliga schema och behöver inte läsas in igen" in CREATOR
    assert "schedule_locked" in CREATOR
    assert "UPDATE tournaments SET schedule_dirty=0,is_published=0" in CREATOR


def test_smart_import_reuses_same_image_for_schedule_instead_of_second_upload():
    assert 'if "Schema" in _selected_sections and _smart_image is not None:' in APP
    assert 'extract_cup_setup_from_documents' in APP
    assert 'st.session_state[f"schedule_existing_import_prefill_{tid}"] = _structured' in APP
    assert 'st.session_state[f"schedule_existing_import_from_smart_{tid}"] = True' in APP
    assert "du behöver inte läsa in bilden igen" in SCHEDULE
    assert "Nya bildimporter ska inte behöva läsas in igen" in SCHEDULE


def test_imported_schedule_stays_manually_editable_without_regeneration():
    assert "Redigera befintligt schema manuellt" in SCHEDULE
    assert "Ändra en ospelad match utan att generera om resten av schemat" in SCHEDULE
