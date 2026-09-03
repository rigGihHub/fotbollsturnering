from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
SETUP = (ROOT / "cupnavi_core" / "initial_setup_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_v326_version():
    assert VERSION == "2026.09.03-424-PUBLIC-INFO-ROUNDTRIP-CUT"


def test_setup_has_fast_track_to_teams_after_minimum_setup():
    assert "Redo att lägga till lag" in SETUP
    assert "Fortsätt → Lägg till lag" in SETUP
    assert '_fast_track_ready = bool(class_rows) and _planned_total > 0 and valid_windows and not _addresses_to_verify' in SETUP
    assert 'st.session_state[f"admin_page_{tournament_id}"] = "Lag"' in SETUP


def test_admin_overview_replaces_duplicate_fast_track_with_one_next_step():
    block = APP[APP.index('elif admin_page == "Adminöversikt":'):APP.index('if admin_page == "Cupinställningar":')]
    assert "⚡ Snabbväg till publicerad cup" not in block
    assert 'key=f"dashboard_next_step_{tid}"' in block
    assert "recommend_next_step(" in block


def test_advanced_setup_remains_available():
    assert 'st.markdown("### 3. Rekommenderat tävlingsformat")' in SETUP
    assert 'st.markdown("### 5. Vad är viktigast i schemat?")' in SETUP
    assert 'st.markdown("### 6. Arrangemang & deltagarservice")' in SETUP
