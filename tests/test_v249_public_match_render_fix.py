
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARD = (ROOT / "cupnavi_core/public_match_cards.py").read_text(encoding="utf-8")

def test_public_match_card_uses_compact_html_string():
    assert "card_html = (" in CARD
    assert "st.markdown(card_html, unsafe_allow_html=True)" in CARD
    assert '<div class="public-match-secondary">{weather_html}{referee_html}</div>' in CARD

def test_referee_html_is_not_left_as_indented_markdown_fragment():
    assert "referee_html = (" in CARD
    assert 'class="match-referee"' in CARD
    assert 'st.markdown(\\n            f"""' not in CARD

def test_public_match_card_dynamic_text_is_escaped():
    assert 'html.escape(str(match_row["stage"]))' in CARD
    assert 'html.escape(public_referee_label(match_row) or "Ej tillsatt")' in CARD
    assert 'html.escape(center_text)' in CARD
