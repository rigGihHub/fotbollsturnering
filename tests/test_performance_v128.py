from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_admin_dashboard_reuses_single_workflow_count_query():
    text = app_text()
    start = text.index('elif admin_page == "Adminöversikt":')
    end = text.index('if admin_page == "Kontroller":', start + 10)
    block = text[start:end]
    assert block.count('_admin_workflow_counts(tid)') == 1
    assert 'workflow_counts = _admin_workflow_counts(tid)' in block
    assert 'overview_counts = one_row(' not in block


def test_control_center_reuses_fairness_match_rows():
    text = app_text()
    assert 'control_matches = fairness_matches' in text


def test_dashboard_navigation_uses_callbacks_without_manual_rerun():
    text = app_text()
    start = text.index('elif admin_page == "Adminöversikt":')
    block = text[start:start+18000]
    assert 'on_click=_set_admin_page' in block
    # v337 replaces the duplicate quick-action grid with one primary next-step callback.
    assert 'quick_actions =' not in block
    primary = block[block.index('with st.container(border=True):'):block.index('checkin_enabled =')]
    assert 'on_click=_set_admin_page' in primary
    assert 'st.rerun()' not in primary


def test_public_tracking_is_throttled_to_reduce_cloud_writes():
    text = app_text()
    assert 'total_seconds() >= 300' in text
