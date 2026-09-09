from pathlib import Path

def test_event_save_button_is_removed():
    app = Path("app.py").read_text(encoding="utf-8")
    view = Path("cupnavi_core/admin_match_events_view.py").read_text(encoding="utf-8")
    text = app + view
    assert 'Spara mål och assist för' not in text
    assert "Händelser sparas automatiskt" in text

def test_event_autosave_only_writes_changed_rows():
    view = Path("cupnavi_core/admin_match_events_view.py").read_text(encoding="utf-8")
    logic = Path("cupnavi_core/match_event_logic.py").read_text(encoding="utf-8")
    assert "prepare_changed_event_rows(" in view
    assert "new_values != previous_values" in logic

def test_invalid_event_totals_do_not_autosave():
    text = Path("cupnavi_core/admin_match_events_view.py").read_text(encoding="utf-8")
    assert 'changed_event_rows and event_validation["ok"]' in text
    assert 'changed_event_rows and not event_validation["ok"]' in text

def test_both_result_and_event_autosave_show_saved_confirmation():
    app = Path("app.py").read_text(encoding="utf-8")
    admin_view = Path("cupnavi_core/admin_match_events_view.py").read_text(encoding="utf-8")
    reporter_view = Path("cupnavi_core/match_reporter_workspace_view.py").read_text(encoding="utf-8")
    text = app + admin_view + reporter_view
    assert text.count("✓ Sparat automatiskt") >= 2
    assert 'icon="✅"' in text
