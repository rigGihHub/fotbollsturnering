from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_schema_v10_adds_internal_team_messages():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = " in text
    assert "team_messaging_v108" in text
    assert "CREATE TABLE IF NOT EXISTS team_messages" in text
    assert "recipient_type" in text
    assert "recipient_team_id" in text


def test_team_portal_can_message_organizer_or_another_team():
    text = app_text()
    assert 'st.subheader("Meddelanden")' in text
    assert '("organizer", None, "Arrangören")' in text
    assert 'recipient_type=recipient_type' in text
    assert 'recipient_team_id=recipient_team_id' in text
    assert '"Inkorg", "Skickat"' in text


def test_admin_has_message_inbox_and_can_reply():
    text = app_text()
    assert 'with st.expander("Lagmeddelanden", expanded=False)' in text
    assert 'organizer_inbox_label' in text
    assert '"Skriv till lag", "Alla meddelanden"' in text
    assert 'SV: {msg[' in text
    assert 'sender_type="organizer"' not in text  # helper uses positional sender type
    assert '_send_team_message(' in text


def test_only_player_names_use_protected_ui():
    text = app_text()
    assert "Skyddad spelare – visa inte namn publikt" in text
    assert "Skyddade kontaktuppgifter" not in text
    assert "responsible_contact_protected" in text  # legacy DB compatibility only
