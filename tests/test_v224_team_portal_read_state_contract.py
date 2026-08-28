
from pathlib import Path
import ast

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")


def _portal():
    tree=ast.parse(APP)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="render_team_portal")
    lines=APP.splitlines()
    return "\n".join(lines[node.lineno-1:node.end_lineno])


def test_team_messages_are_not_auto_marked_read_on_tab_render():
    portal=_portal()
    assert "Markera alla som lästa" in portal
    assert "portal_mark_messages_read_" in portal
    assert "UPDATE team_messages SET read_at=?" not in portal


def test_contact_form_uses_optimistic_writer():
    portal=_portal()
    assert "_save_team_contact_if_unchanged(" in portal
    assert "Kontaktuppgifterna ändrades av någon annan" in portal


def test_admin_inbox_has_explicit_unread_action():
    block=APP[APP.index('with st.expander("Lagmeddelanden", expanded=False)'):]
    assert "organizer_inbox_label" in block
    assert "admin_mark_messages_read_" in block
    assert "_mark_team_messages_read(" in block


def test_contact_conflict_feedback_survives_rerun():
    portal=_portal()
    assert "contact_notice_key=" in portal
    assert 'st.session_state[contact_notice_key]=' in portal
    assert "Senaste uppgifter har laddats." in portal
