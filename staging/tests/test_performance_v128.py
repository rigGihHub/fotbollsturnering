from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_admin_dashboard_reuses_single_workflow_count_query():
    text = app_text()
    start = text.index('elif admin_page == "Adminöversikt":')
    end = text.index('if admin_page == "Kontroller":', start + 10)
    block = text[start:end]
    assert 'workflow_counts = ux_counts' in block
    assert 'overview_counts = one_row(' not in block


def test_control_center_reuses_fairness_match_rows():
    text = app_text()
    assert 'control_matches = fairness_matches' in text


def test_dashboard_navigation_uses_callbacks_without_manual_rerun():
    text = app_text()
    start = text.index('elif admin_page == "Adminöversikt":')
    block = text[start:start+18000]
    assert 'on_click=_set_admin_page' in block
    # The quick actions must not perform the old second explicit rerun.
    quick = block[block.index('quick_actions ='):block.index('preview_cols =')]
    assert 'st.rerun()' not in quick


def test_public_tracking_is_throttled_to_reduce_cloud_writes():
    text = app_text()
    assert 'total_seconds() >= 300' in text
