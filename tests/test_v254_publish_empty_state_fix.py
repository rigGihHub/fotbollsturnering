
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")

def test_empty_state_uses_keyword_only_symbol():
    assert 'render_empty_state(\n            "Inga deltagare ännu",' in APP
    assert 'symbol="👥"' in APP
    assert 'render_empty_state("Inga deltagare ännu", "Lägg till första laget/deltagaren eller använd Import för flera på en gång.", "👥")' not in APP

def test_publish_button_is_single_left_primary_action():
    block=APP[APP.index("# v159: Publicering"):APP.index("# Cupens livscykel")]
    assert 'mobile_publish_col, _publish_spacer = st.columns([1, 1])' in block
    assert 'f"📣 {_publish_action_label}"' in block
    assert 'with st.expander("Fler publiceringsval", expanded=False):' in block

def test_publish_label_knows_first_publish_vs_update():
    assert '"published_once": "INTEGER NOT NULL DEFAULT 0"' in APP
    assert "published_once=1" in APP
    assert '_publish_action_label = "Uppdatera" if _has_been_published else "Publicera"' in APP

def test_unpublish_does_not_reset_publication_history():
    helper=APP[APP.index("def _set_publication_if_current"):APP.index("def _set_lifecycle_if_current")]
    unpublish=helper[helper.index("else:"):]
    assert "published_once=0" not in unpublish
