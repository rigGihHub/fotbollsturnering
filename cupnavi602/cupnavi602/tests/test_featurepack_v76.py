from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def app_text():
    return (ROOT / "app.py").read_text(encoding="utf-8")


def test_qr_sharing_uses_direct_cup_query_parameter():
    text = app_text()
    assert "def public_cup_url(" in text
    assert '"?cup="' not in text  # avoid accidentally hardcoding broken literal form
    assert "st.query_params.get(\"cup\")" in text
    assert "Ladda ner QR-kod" in text
    assert "qrcode.make" in text


def test_sponsor_management_and_public_partners_exist():
    text = app_text()
    info = (ROOT / "cupnavi_core" / "public_info_view.py").read_text(encoding="utf-8")
    assert 'if admin_page == "Sponsorer":' in text
    assert "INSERT INTO sponsors(" in text
    assert "UPDATE sponsors SET" in text
    assert "DELETE FROM sponsors" in text
    assert 'with st.expander("🤝 " + tr("Partners")):' in info
    assert "Cupens partners" in text


def test_functionaries_can_be_administered_and_published_selectively():
    text = app_text()
    assert 'if admin_page == "Funktionärer":' in text
    assert "INSERT INTO functionaries(" in text
    assert "public_contact=1" in text
    assert "Funktionärer" in text


def test_drag_and_drop_schedule_adjustment_exists():
    text = app_text()
    schedule_view = (ROOT / "cupnavi_core" / "schedule_workspace_view.py").read_text(encoding="utf-8")
    assert "sort_items(" in text or "sort_items(" in schedule_view
    assert "Tillämpa drag-and-drop-ordningen" in schedule_view
    assert "validate_schedule(tid, tournament, rules)" in schedule_view
    assert "schedule_locked" in schedule_view


def test_import_supports_csv_and_xlsx_for_teams_and_players():
    text = app_text()
    assert 'if admin_page == "Import":' in text
    assert 'type=["csv", "xlsx"]' in text
    assert "pd.read_csv" in text
    assert "pd.read_excel" in text
    assert "Importera lagen" in text
    assert "Importera trupperna" in text

