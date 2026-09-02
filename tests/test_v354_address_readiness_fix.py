from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_v354_version():
    assert VERSION == "2026.09.02-390-PUBLIC-SHARE-TOPLIST-UX"
    assert VERSION in APP

def test_pitch_metadata_reads_saved_address_verification():
    assert "SELECT tournament_id,pitch_number,name,address,address_verified FROM pitches" in APP
    assert "ensure_v26_schema_compat(con)" in APP

def test_checkbox_state_is_readiness_source_in_same_render():
    assert "_pitch_address_status=[]" in SETUP
    assert "_pitch_address_status.append((address.strip(), bool(verified)))" in SETUP
    assert "_addresses_to_verify=[address for address, verified in _pitch_address_status if address and not verified]" in SETUP
    assert "_pitch_rows_current=ensure_pitch_definitions" not in SETUP
    assert "disabled=not _fast_track_ready" in SETUP

def test_address_change_still_resets_verification():
    assert "address_verified=0" in APP
