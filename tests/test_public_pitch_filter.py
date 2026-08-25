from pathlib import Path

def test_public_schedule_has_pitch_filter():
    text = Path("app.py").read_text(encoding="utf-8")
    assert '"En plan"' in text
    assert '"Välj plan"' in text
    assert 'key=f"{key_prefix}_pitch_{tournament_id}"' in text

def test_pitch_filter_matches_pitch_number():
    text = Path("app.py").read_text(encoding="utf-8")
    assert 'int(match_row["pitch_number"] or 0) == selected_pitch' in text

def test_pitch_filter_keeps_next_match_overview_single_source():
    text = Path("app.py").read_text(encoding="utf-8")
    matcher=text[text.index('if public_page == "Matcher":'):text.index('if public_page == "Statistik":')]
    assert 'class="cn-next-match"' not in matcher
    assert "Cupen just nu" in matcher
