from pathlib import Path


def app_text():
    return Path("app.py").read_text(encoding="utf-8")


def test_qr_sharing_uses_direct_cup_query_parameter():
    text = app_text()
    assert "def public_cup_url(" in text
    assert '"?cup="' not in text  # avoid accidentally hardcoding broken literal form
    assert "st.query_params.get(\"cup\")" in text
    assert "Ladda ner QR-kod" in text
    assert "qrcode.make" in text


def test_sponsor_management_and_public_partners_exist():
    text = app_text()
    assert 'if admin_page == "Sponsorer":' in text
    assert "INSERT INTO sponsors(" in text
    assert "UPDATE sponsors SET" in text
    assert "DELETE FROM sponsors" in text
    assert "with partners_tab:" in text
    assert "Cupens partners" in text


def test_functionaries_can_be_administered_and_published_selectively():
    text = app_text()
    assert 'if admin_page == "Funktionärer":' in text
    assert "INSERT INTO functionaries(" in text
    assert "public_contact=1" in text
    assert "Funktionärer" in text


def test_drag_and_drop_schedule_adjustment_exists():
    text = app_text()
    assert "sort_items(" in text
    assert "Tillämpa drag-and-drop-ordningen" in text
    assert "validate_schedule(tid, tournament, rules)" in text
    assert "schedule_locked" in text


def test_import_supports_csv_and_xlsx_for_teams_and_players():
    text = app_text()
    assert 'if admin_page == "Import":' in text
    assert 'type=["csv", "xlsx"]' in text
    assert "pd.read_csv" in text
    assert "pd.read_excel" in text
    assert "Importera lagen" in text
    assert "Importera trupperna" in text

