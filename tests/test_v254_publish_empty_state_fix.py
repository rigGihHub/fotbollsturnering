from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VIEW=(ROOT/"cupnavi_core"/"admin_publication_view.py").read_text(encoding="utf-8")
PURE=(ROOT/"cupnavi_core"/"admin_publication.py").read_text(encoding="utf-8")


def test_empty_state_uses_keyword_only_symbol():
    assert 'render_empty_state(\n            "Inga deltagare ännu",' in APP
    assert 'symbol="👥"' in APP
    assert 'render_empty_state("Inga deltagare ännu", "Lägg till första laget/deltagaren eller använd Import för flera på en gång.", "👥")' not in APP


def test_publish_button_is_single_left_primary_action():
    block=VIEW[VIEW.index('# v159: Publicering'):VIEW.index('def render_admin_lifecycle_controls')]
    assert 'mobile_publish_col, _publish_spacer = st.columns([1, 1])' in block
    assert 'f"📣 {action_label}"' in block
    assert 'with st.expander("Fler publiceringsval", expanded=False):' in block


def test_publish_label_knows_first_publish_vs_update():
    assert '"published_once": "INTEGER NOT NULL DEFAULT 0"' in APP
    assert "published_once=1" in APP
    assert 'return "Uppdatera" if published_once else "Publicera"' in PURE


def test_unpublish_does_not_reset_publication_history():
    helper=APP[APP.index("def _set_publication_if_current"):APP.index("def _set_lifecycle_if_current")]
    unpublish=helper[helper.index("else:"):]
    assert "published_once=0" not in unpublish
