from pathlib import Path

def test_organizer_phone_is_persisted():
    text=Path("app.py").read_text(encoding="utf-8")
    assert "organizer_phone TEXT" in text
    assert "ALTER TABLE tournaments ADD COLUMN organizer_phone TEXT" in text
    assert "organizer_phone=?" in text

def test_admin_can_enter_organizer_phone():
    text=Path("app.py").read_text(encoding="utf-8")
    assert '"Arrangörens telefonnummer"' in text
    assert 'edited_organizer_phone.strip()' in text

def test_public_information_has_click_to_call():
    app=Path("app.py").read_text(encoding="utf-8")
    info=Path("cupnavi_core/public_info_view.py").read_text(encoding="utf-8")
    combined=app+info
    assert "Kontakta arrangören" in combined
    assert "cn-call-button" in combined
    assert "href='tel:" in info
