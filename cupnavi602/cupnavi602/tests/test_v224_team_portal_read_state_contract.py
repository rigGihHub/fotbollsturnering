
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
APP=(ROOT/"app.py").read_text(encoding="utf-8")
VIEW=(ROOT/"cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")
REPO=(ROOT/"cupnavi_core/team_portal_repository.py").read_text(encoding="utf-8")


def _portal():
    return VIEW


def test_team_messages_are_not_auto_marked_read_on_tab_render():
    portal=_portal()
    assert "Markera alla som lästa" in portal
    assert "portal_mark_messages_read_" in portal
    assert "UPDATE team_messages SET read_at=?" not in portal


def test_contact_form_uses_optimistic_writer():
    portal=_portal()
    assert "deps.save_team_contact_if_unchanged(" in portal
    assert "Kontaktuppgifterna ändrades av någon annan" in portal


def test_admin_inbox_has_explicit_unread_action():
    block=APP[APP.index('if st.toggle("Lagmeddelanden", value=False, key=f"lazy_team_messages_{tid}"'):]
    assert "organizer_inbox_label" in block
    assert "admin_mark_messages_read_" in block
    assert "_mark_team_messages_read(" in block


def test_contact_conflict_feedback_survives_rerun():
    portal=_portal()
    assert "contact_notice_key=" in portal
    assert 'st.session_state[contact_notice_key]=' in portal
    assert "Senaste uppgifter har laddats." in portal
