from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MATCHES = (ROOT / 'cupnavi_core' / 'public_matches_view.py').read_text()
FILTERS = (ROOT / 'cupnavi_core' / 'public_match_filters_view.py').read_text()
WORKSPACE = (ROOT / 'cupnavi_core' / 'public_workspace_view.py').read_text()
VERSION = (ROOT / 'VERSION.txt').read_text().strip()


def test_v538_version_and_dataset_controls_force_parent_rerun():
    assert VERSION == '2026.09.08-538-FRAGMENT-DATASET-RERUN-GUARD'
    assert 'def _rerun_full_public_app()' in MATCHES
    assert 'st.rerun(scope="app")' in MATCHES
    assert 'on_change=_rerun_full_public_app' in MATCHES
    assert 'def _show_more_public_matches()' in MATCHES
    show_more = MATCHES[MATCHES.index('def _show_more_public_matches()'):]
    assert 'st.rerun(scope="app")' in show_more[:700]


def test_v538_filter_mode_widens_parent_snapshot_and_skips_resort():
    assert 'on_filter_mode_change=None' in FILTERS
    assert 'input_already_sorted=False' in FILTERS
    assert 'on_change=on_filter_mode_change' in FILTERS
    assert 'list(filtered) if input_already_sorted else sort_public_matches(filtered)' in FILTERS
    assert 'on_filter_mode_change=lambda: st.rerun(scope="app")' in WORKSPACE
    assert 'input_already_sorted=True' in WORKSPACE


def test_v538_exact_totals_avoid_played_match_goal_rescan():
    assert 'if total_goals is None:' in MATCHES
    assert 'summary_total_goals = sum(' in MATCHES
    assert 'else:\n        summary_total_goals = int(total_goals or 0)' in MATCHES
