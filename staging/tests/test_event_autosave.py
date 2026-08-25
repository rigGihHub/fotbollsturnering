from pathlib import Path

def test_event_save_button_is_removed():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'Spara mål och assist för' not in text
    assert "Händelser sparas automatiskt" in text

def test_event_autosave_only_writes_changed_rows():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "changed_event_rows" in text
    assert "new_values != previous_values" in text

def test_invalid_event_totals_do_not_autosave():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'changed_event_rows and event_validation["ok"]' in text
    assert 'changed_event_rows and not event_validation["ok"]' in text

def test_both_result_and_event_autosave_show_saved_confirmation():
    text = Path("app.py").read_text(encoding="utf-8")
    assert text.count("✓ Sparat automatiskt") >= 2
    assert 'icon="✅"' in text
