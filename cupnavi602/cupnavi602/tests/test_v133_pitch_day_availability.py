from pathlib import Path

APP=Path("app.py").read_text(encoding="utf-8")
MIG=Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")

def test_pitch_day_windows_schema_exists():
    assert "LATEST_SCHEMA_VERSION = " in MIG
    import re
    assert int(re.search(r"LATEST_SCHEMA_VERSION = (\d+)", MIG).group(1)) >= 17
    assert "CREATE TABLE IF NOT EXISTS pitch_day_windows" in MIG
    assert "PRIMARY KEY(tournament_id,pitch_number,play_date)" in MIG

def test_setup_collects_per_pitch_per_day_windows():
    assert "ensure_pitch_day_windows" in APP
    assert 'f"Plan {pitch}"' in APP
    assert 'save_pitch_day_window' in APP

def test_scheduler_uses_pitch_specific_windows():
    assert "pitch_bounds(day,pitch)" in APP
    assert "valid_pitch_start_for" in APP
    assert "validation_windows.get((start_at.date().isoformat(),pitch_no)" in APP

def test_old_match_schedule_controls_removed_from_admin_overview():
    block=APP[APP.index('st.markdown("#### Match- och schemaregler")'):APP.index('overview_autosave_changed = any([',APP.index('st.markdown("#### Match- och schemaregler")'))]
    assert 'number_input("Antal planer"' not in block
    assert 'Sista plantid' not in block
    assert 'Första avspark' not in block
