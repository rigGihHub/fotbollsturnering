from pathlib import Path

def app_text():
    return Path("app.py").read_text(encoding="utf-8")

def test_offers_have_database_table():
    text=app_text()
    assert "CREATE TABLE IF NOT EXISTS offers" in text
    assert "discount_code TEXT" in text
    assert "active INTEGER NOT NULL DEFAULT 1" in text

def test_offers_exist_in_admin_and_public_navigation():
    text=app_text()
    assert '("Erbjudanden", tr("Erbjudanden"))' in text
    assert 'tr("Slutspel")' in text
    assert 'if admin_page == "Erbjudanden":' in text
    assert 'if public_section == tr("Erbjudanden"):' in text

def test_admin_can_create_edit_hide_and_delete_offers():
    text=app_text()
    assert "INSERT INTO offers(" in text
    assert "UPDATE offers SET" in text
    assert "DELETE FROM offers" in text
    assert "Visa i turneringsvyn" in text

def test_public_only_shows_active_offers():
    text=app_text()
    assert "WHERE tournament_id=? AND active=1" in text
    assert "Rabattkod" in text
    assert "Öppna erbjudandet" in text

def test_instructions_include_offers():
    text=app_text()
    guide=text[text.index('if admin_page == "Instruktioner":'):text.index('elif admin_page == "Adminöversikt":')]
    assert '"page": "Erbjudanden"' in guide
    assert "restaurangrabatter eller rabattkoder" in guide
