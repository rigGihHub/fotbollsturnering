from pathlib import Path

def test_blocking_warning_state_is_built_before_checkbox():
    text = Path("cupnavi_core/admin_publication_view.py").read_text(encoding="utf-8")
    definition = text.index("blocking_warnings, advisory_warnings = split_schedule_warnings(schedule_warnings)")
    checkbox = text.index('sidebar_warnings_approved = st.sidebar.checkbox(')
    assert definition < checkbox
