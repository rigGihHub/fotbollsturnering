
from pathlib import Path
APP = Path(__file__).resolve().parents[1] / "cupnavi_core" / "public_presentation_view.py"
def test_compact_final_only_bracket():
    text = APP.read_text(encoding="utf-8")
    assert "compact_final_only = stage_count == 1 and first_count == 1" in text
    assert "play_height = card_height + 44" in text
    assert "card_width = 320 if compact_final_only else 250" in text
