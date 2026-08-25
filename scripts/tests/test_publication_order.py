from pathlib import Path

def test_blocking_warning_variable_is_defined_before_checkbox():
    text = Path("app.py").read_text(encoding="utf-8")
    definition = text.index("blocking_sidebar_warnings = [")
    checkbox = text.index('sidebar_warnings_approved = st.sidebar.checkbox(')
    assert definition < checkbox
