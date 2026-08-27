
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
LOGIC=(ROOT/"cupnavi_core/initial_setup_logic.py").read_text(encoding="utf-8")
VERSION=(ROOT/"VERSION.txt").read_text(encoding="utf-8").strip()

def test_setup_uses_shared_capacity_engine():
    assert "def available_pitch_minutes(" in LOGIC
    assert "def estimated_match_length_minutes(" in LOGIC
    assert "def estimated_capacity_slots(" in LOGIC
    assert "estimated_capacity_slots(" in APP

def test_optional_service_fields_use_progressive_disclosure():
    assert "if changing_rooms_enabled:" in APP
    assert "if show_prices_enabled:" in APP

def test_release_is_v214():
    assert VERSION=="2026.08.27-215-INITIAL-SETUP-HARDENING-PHASE2"
    assert "Version v.1.215" in APP
