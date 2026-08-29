
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
SETUP=(ROOT/"cupnavi_core"/"initial_setup_view.py").read_text(encoding="utf-8")


def test_setup_priority_write_has_explicit_change_guard():
    setup=SETUP
    assert "priority_order_changed(_new_priority_items, _saved_priorities)" in setup


def test_team_request_priorities_only_write_changed_rows():
    setup=SETUP
    assert "_request_priority_updates=[]" in setup
    assert 'if int(_row_value(row,"request_priority",0) or 0) != pos:' in setup
    assert "con.executemany(" in setup
