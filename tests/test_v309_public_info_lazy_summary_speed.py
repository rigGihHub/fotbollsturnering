from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INFO = (ROOT / "cupnavi_core" / "public_info_view.py").read_text(encoding="utf-8")
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()


def test_release_version():
    assert VERSION == "2026.09.03-423-PUBLIC-INFO-COLD-START"


def test_venue_snapshot_is_reused_instead_of_second_query():
    assert "venue_points_public = all_rows(" in INFO
    assert INFO.count("SELECT * FROM venue_points WHERE tournament_id=?") == 1
    assert 'SELECT * FROM venue_points WHERE tournament_id=? ORDER BY sort_order,id' not in INFO
    assert 'Do not repeat the same places' in INFO


def test_finished_cup_summary_is_explicitly_lazy():
    marker = 'show_cup_summary = st.toggle('
    assert marker in INFO
    toggle_pos = INFO.index(marker)
    scorer_pos = INFO.index('top_scorer_row = one_row(', toggle_pos)
    teams_pos = INFO.index('summary_teams = all_rows(', toggle_pos)
    if_pos = INFO.index('if show_cup_summary:', toggle_pos)
    assert if_pos < scorer_pos < teams_pos
    assert '"🏁 Visa cupsummering"' in INFO


def test_core_write_paths_are_not_added_to_public_info_speed_change():
    assert "UPDATE matches" not in INFO
    assert "UPDATE schedule_rules" not in INFO
