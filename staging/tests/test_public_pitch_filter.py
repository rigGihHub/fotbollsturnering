from pathlib import Path

def test_public_schedule_has_pitch_filter():
    text = Path("app.py").read_text(encoding="utf-8")
    assert '"En plan"' in text
    assert '"Välj plan"' in text
    assert 'key=f"{key_prefix}_pitch_{tournament_id}"' in text

def test_pitch_filter_matches_pitch_number():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'int(match_row["pitch_number"] or 0) == selected_pitch' in text

def test_next_match_label_handles_pitch_filter():
    text = Path("app.py").read_text(encoding="utf-8")
    assert "Nästa match på vald plan" in text
