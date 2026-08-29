from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8") + Path("cupnavi_core/team_portal_view.py").read_text(encoding="utf-8")


def test_schema_v9_contains_privacy_and_admin_code_fields():
    text = Path("cupnavi_core/migrations.py").read_text(encoding="utf-8")
    assert "LATEST_SCHEMA_VERSION = " in text
    assert "admin_code TEXT" in text
    assert "responsible_contact_protected" in text
    assert "first_name TEXT" in text
    assert "last_name TEXT" in text
    assert "is_protected" in text


def test_successful_logins_rerun_to_hide_credentials():
    text = app_text()
    assert 'st.session_state["admin_authenticated"] = True\n            st.rerun()' in text
    assert 'st.session_state["reporter_authenticated"] = True' in text
    assert 'st.session_state["reporter_auth_scope"]' in text
    assert 'st.rerun()' in text
    assert 'st.session_state["participant_portal_auth"]' in text
    assert 'st.rerun()' in text


def test_admin_has_visible_team_code_table_and_bulk_code_creation():
    text = app_text()
    assert '"Lagkod": visible_code' in text
    assert "Skapa/ersätt koder för alla som saknar visningsbar kod" in text
    assert "admin_code=excluded.admin_code" in text


def test_team_portal_requires_split_name_and_birth_year():
    text = app_text()
    assert 'pfirst = pc1.text_input("Förnamn")' in text
    assert 'plast = pc2.text_input("Efternamn")' in text
    assert 'pbirth = pc4.number_input("Födelseår"' in text
    assert "Ange både förnamn och efternamn." in text


def test_protected_player_name_is_hidden_in_public_stats():
    text = app_text() + Path("cupnavi_core/public_statistics_view.py").read_text(encoding="utf-8")
    assert "Skyddad spelare" in text
    assert "players.is_protected" in text
    assert "Skyddade kontaktuppgifter – får inte visas publikt" not in text
    assert "Skyddade kontaktuppgifter – visas aldrig publikt" not in text
