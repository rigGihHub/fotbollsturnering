from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app.py"

def test_v138_public_matches_fix_is_preserved():
    text = APP.read_text(encoding="utf-8")
    assert "def weather_for_match" in text
    assert "except (TypeError, ValueError)" in text

def test_weather_for_match_tolerates_invalid_start():
    text = APP.read_text(encoding="utf-8")
    block = text[text.index("def weather_for_match"):text.index("def weather_label")]
    assert "except (TypeError, ValueError)" in block
    assert "str(scheduled_start)" in block

def test_public_weather_render_is_guarded():
    text = APP.read_text(encoding="utf-8")
    assert 'weather_text = "Väderprognosen kan inte visas för den här matchen."' in text
    assert "_row_value(match_row, 'referee_id')" in text
